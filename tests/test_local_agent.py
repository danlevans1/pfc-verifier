from app.local_agent import (
    authorize_tool,
    make_tool_authorization_record,
    run_governed_tool,
    verify_record,
)


def test_tool_requires_human_approval():
    decision = authorize_tool("web_search", False)
    assert decision["decision"] == "deny"


def test_tool_can_be_approved():
    decision = authorize_tool("web_search", True)
    assert decision["decision"] == "allow"


def test_authorization_record_verifies():
    record = make_tool_authorization_record("web_search", True)
    assert verify_record(record) is True


def test_tampered_authorization_is_rejected():
    record = make_tool_authorization_record("web_search", True)
    record["authorization"]["tool"] = "file_delete"
    assert verify_record(record) is False


def test_authorization_cannot_be_reused_for_another_tool():
    record = make_tool_authorization_record("web_search", True)
    result = run_governed_tool("file_delete", record)

    assert result["status"] == "denied"
    assert result["reason"] == "authorization does not match tool"


def test_local_agent_receipt_integration():
    from app.local_agent import run_local_agent_with_receipt

    result = run_local_agent_with_receipt(
        "Reply with exactly: PFC_TEST_RECEIPT_OK"
    )

    assert result["execution"]["output"]["content"] == "PFC_TEST_RECEIPT_OK"
    assert result["verification"]["valid"] is True
    assert result["verification"]["checks"]["cryptographicSignature"] == "PASS"


def _prepared_directory_listing():
    return {
        "status": "awaiting_human_approval",
        "tool": "list_current_directory",
        "proposal": {
            "status": "proposed",
            "proposal": {
                "tool": "list_current_directory",
                "path": ".",
                "reason": "test",
            },
            "model": "test-model",
            "provider": "test-provider",
        },
        "validation": {
            "decision": "allow",
            "tool": "list_current_directory",
            "reason": "tool is permitted for authorization review",
        },
    }


def test_governed_action_executes_only_after_approval():
    from app.local_agent import complete_governed_action

    prepared = _prepared_directory_listing()
    result = complete_governed_action(prepared, True)

    assert result["status"] == "executed"
    assert result["execution"]["status"] == "executed"
    assert "files" in result["execution"]["result"]
    assert result["verification"]["valid"] is True


def test_governed_action_denial_prevents_execution():
    from app.local_agent import complete_governed_action

    prepared = _prepared_directory_listing()
    result = complete_governed_action(prepared, False)

    assert result["status"] == "denied"
    assert result["execution"]["status"] == "denied"
    assert "result" not in result["execution"]
    assert result["verification"]["valid"] is True


def test_authorization_cannot_be_consumed_twice():
    from app.local_agent import (
        prepare_governed_action,
        make_bound_tool_authorization_record,
        consume_authorization,
    )

    prepared = prepare_governed_action(
        "Show me what files are in the current PFC project directory."
    )

    authorization = make_bound_tool_authorization_record(prepared, True)

    first = consume_authorization(authorization)
    second = consume_authorization(authorization)

    assert first["decision"] == "allow"
    assert second["decision"] == "deny"
    assert second["reason"] == "authorization has already been consumed"


def test_read_project_file_allows_file_inside_project():
    from app.local_agent import make_tool_authorization_record, read_project_file

    authorization = make_tool_authorization_record("read_project_file", True)
    result = read_project_file("README.md", authorization)

    assert result["status"] == "executed"
    assert result["result"]["path"].endswith("/README.md")
    assert result["result"]["content"]


def test_read_project_file_blocks_path_escape():
    from app.local_agent import make_tool_authorization_record, read_project_file

    authorization = make_tool_authorization_record("read_project_file", True)
    result = read_project_file("../.zshrc", authorization)

    assert result["status"] == "denied"
    assert result["reason"] == "path escapes PFC project root"


def test_file_read_proposal_blocks_path_escape():
    from app.local_agent import validate_tool_proposal

    proposal = {
        "status": "proposed",
        "proposal": {
            "tool": "read_project_file",
            "path": "../.zshrc",
            "reason": "test",
        },
    }

    result = validate_tool_proposal(proposal)

    assert result["decision"] == "deny"
    assert result["reason"] == "path escapes PFC project root"


def test_corrupted_replay_state_fails_closed(tmp_path, monkeypatch):
    import app.local_agent as local_agent

    state_file = tmp_path / ".pfc_consumed_authorizations.json"
    state_file.write_text("{not valid json")

    monkeypatch.setattr(
        local_agent,
        "_CONSUMED_AUTHORIZATIONS_FILE",
        state_file,
    )

    result = local_agent.consume_authorization(
        {"authorization_id": "TEST-CORRUPT-STATE"}
    )

    assert result["decision"] == "deny"
    assert result["reason"] == "authorization replay state is unreadable"


def test_read_project_file_blocks_oversized_file(tmp_path, monkeypatch):
    import app.local_agent as local_agent

    large_file = tmp_path / "large.txt"
    large_file.write_bytes(b"x" * 1_000_001)

    monkeypatch.setattr(
        local_agent,
        "PFC_PROJECT_ROOT",
        tmp_path,
    )

    authorization = local_agent.make_tool_authorization_record(
        "read_project_file",
        True,
    )

    result = local_agent.read_project_file(
        "large.txt",
        authorization,
    )

    assert result["status"] == "denied"
    assert result["reason"] == "file exceeds maximum readable size"


def test_concurrent_authorization_consumption_allows_only_one(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    state_file = tmp_path / ".pfc_consumed_authorizations.json"
    lock_file = tmp_path / ".pfc_consumed_authorizations.lock"

    script = f'''
import json
from pathlib import Path
import app.local_agent as local_agent

local_agent._CONSUMED_AUTHORIZATIONS_FILE = Path(r"{state_file}")
local_agent._AUTHORIZATION_LOCK_FILE = Path(r"{lock_file}")

result = local_agent.consume_authorization(
    {{"authorization_id": "CONCURRENT-TEST"}}
)

print(json.dumps(result))
'''

    project_root = Path(__file__).resolve().parent.parent

    first = subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    second = subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    out1, err1 = first.communicate()
    out2, err2 = second.communicate()

    assert first.returncode == 0, err1
    assert second.returncode == 0, err2

    results = [
        json.loads(out1.strip()),
        json.loads(out2.strip()),
    ]

    decisions = sorted(result["decision"] for result in results)

    assert decisions == ["allow", "deny"]


def test_list_project_subdirectory_executes_inside_project():
    from app.local_agent import make_tool_authorization_record, list_current_directory

    authorization = make_tool_authorization_record(
        "list_current_directory",
        True,
    )

    result = list_current_directory(
        authorization,
        "app",
    )

    assert result["status"] == "executed"
    assert result["result"]["path"].endswith("/app")
    assert "local_agent.py" in result["result"]["files"]


def test_list_project_subdirectory_blocks_sensitive_path():
    from app.local_agent import make_tool_authorization_record, list_current_directory

    authorization = make_tool_authorization_record(
        "list_current_directory",
        True,
    )

    result = list_current_directory(
        authorization,
        ".git",
    )

    assert result["status"] == "denied"
    assert result["reason"] == "access to sensitive project path is denied"


def test_directory_proposal_requires_relative_path():
    from app.local_agent import validate_tool_proposal

    proposal = {
        "status": "proposed",
        "proposal": {
            "tool": "list_current_directory",
            "path": "/tmp",
            "reason": "test",
        },
    }

    result = validate_tool_proposal(proposal)

    assert result["decision"] == "deny"
    assert result["reason"] == "absolute paths are not allowed"


def test_write_project_file_denied_without_approval(tmp_path, monkeypatch):
    from pathlib import Path
    import app.local_agent as local_agent

    monkeypatch.setattr(local_agent, "PFC_PROJECT_ROOT", tmp_path)

    prepared = {
        "status": "awaiting_human_approval",
        "tool": "write_project_file",
        "proposal": {
            "status": "proposed",
            "proposal": {
                "tool": "write_project_file",
                "path": "denied.txt",
                "content": "must not be written",
                "reason": "test",
            },
        },
        "validation": {
            "decision": "allow",
            "tool": "write_project_file",
            "reason": "tool is permitted for authorization review",
        },
    }

    result = local_agent.complete_governed_action(prepared, False)

    assert result["status"] == "denied"
    assert not (tmp_path / "denied.txt").exists()


def test_write_project_file_creates_exact_content(tmp_path, monkeypatch):
    import app.local_agent as local_agent

    monkeypatch.setattr(local_agent, "PFC_PROJECT_ROOT", tmp_path)

    prepared = {
        "status": "awaiting_human_approval",
        "tool": "write_project_file",
        "proposal": {
            "status": "proposed",
            "proposal": {
                "tool": "write_project_file",
                "path": "created.txt",
                "content": "exact approved content",
                "reason": "test",
            },
        },
        "validation": {
            "decision": "allow",
            "tool": "write_project_file",
            "reason": "tool is permitted for authorization review",
        },
    }

    result = local_agent.complete_governed_action(prepared, True)

    assert result["status"] == "executed"
    assert (tmp_path / "created.txt").read_text() == "exact approved content"
    assert result["execution"]["result"]["operation"] == "create"
    assert result["verification"]["valid"] is True


def test_write_project_file_blocks_sensitive_path(tmp_path, monkeypatch):
    import app.local_agent as local_agent

    monkeypatch.setattr(local_agent, "PFC_PROJECT_ROOT", tmp_path)
    (tmp_path / ".env").write_text("SECRET=test")

    authorization = local_agent.make_tool_authorization_record(
        "write_project_file",
        True,
    )

    result = local_agent.write_project_file(
        ".env",
        "changed",
        authorization,
    )

    assert result["status"] == "denied"
    assert result["reason"] == "access to sensitive project path is denied"
    assert (tmp_path / ".env").read_text() == "SECRET=test"


def test_write_proposal_blocks_path_escape(tmp_path, monkeypatch):
    import app.local_agent as local_agent

    monkeypatch.setattr(local_agent, "PFC_PROJECT_ROOT", tmp_path)

    proposal = {
        "status": "proposed",
        "proposal": {
            "tool": "write_project_file",
            "path": "../escape.txt",
            "content": "blocked",
            "reason": "test",
        },
    }

    result = local_agent.validate_tool_proposal(proposal)

    assert result["decision"] == "deny"
    assert result["reason"] == "path escapes PFC project root"


def test_write_authorization_is_bound_to_exact_content():
    from app.local_agent import (
        make_bound_tool_authorization_record,
        verify_bound_authorization,
    )

    prepared = {
        "status": "awaiting_human_approval",
        "tool": "write_project_file",
        "proposal": {
            "status": "proposed",
            "proposal": {
                "tool": "write_project_file",
                "path": "example.txt",
                "content": "approved content",
                "reason": "test",
            },
        },
    }

    authorization = make_bound_tool_authorization_record(
        prepared,
        True,
    )

    prepared["proposal"]["proposal"]["content"] = "CHANGED AFTER APPROVAL"

    result = verify_bound_authorization(
        prepared,
        authorization,
    )

    assert result["decision"] == "deny"
    assert result["reason"] == "authorization does not match proposal"
