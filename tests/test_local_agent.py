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


def test_governed_action_executes_only_after_approval():
    from app.local_agent import prepare_governed_action, complete_governed_action

    prepared = prepare_governed_action(
        "Show me what files are in the current PFC project directory."
    )

    result = complete_governed_action(prepared, True)

    assert result["status"] == "executed"
    assert result["execution"]["status"] == "executed"
    assert "files" in result["execution"]["result"]
    assert result["verification"]["valid"] is True


def test_governed_action_denial_prevents_execution():
    from app.local_agent import prepare_governed_action, complete_governed_action

    prepared = prepare_governed_action(
        "Show me what files are in the current PFC project directory."
    )

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
