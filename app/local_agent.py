from datetime import datetime, timezone
import hashlib
import json
import uuid

from app.ollama_adapter import ask_ollama


def _sha256(value: dict) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def authorize(request_type: str, prompt: str) -> dict:
    if not prompt or not prompt.strip():
        return {
            "decision": "deny",
            "reason": "empty prompt",
        }

    if request_type == "model":
        return {
            "decision": "allow",
            "reason": "model-only request",
        }

    if request_type == "tool":
        return {
            "decision": "deny",
            "reason": "tool execution requires separate authorization",
        }

    return {
        "decision": "deny",
        "reason": f"unknown request type: {request_type}",
    }


def run_local_agent(prompt: str, request_type: str = "model") -> dict:
    execution_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    authorization = authorize(request_type, prompt)

    if authorization["decision"] != "allow":
        record = {
            "execution_id": execution_id,
            "request_type": request_type,
            "authorization": authorization,
            "status": "denied",
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        record["record_sha256"] = _sha256(record)
        return record

    result = ask_ollama(prompt)

    completed_at = datetime.now(timezone.utc).isoformat()

    record = {
        "execution_id": execution_id,
        "request_type": request_type,
        "authorization": authorization,
        "provider": result["provider"],
        "model": result["model"],
        "input": {
            "prompt": prompt,
        },
        "output": {
            "content": result["content"],
        },
        "status": "completed" if result["done"] else "incomplete",
        "done_reason": result["done_reason"],
        "started_at": started_at,
        "completed_at": completed_at,
    }

    record["record_sha256"] = _sha256(record)

    return record


def verify_record(record: dict) -> bool:
    supplied_hash = record.get("record_sha256")

    if not supplied_hash:
        return False

    unsigned_record = {
        key: value
        for key, value in record.items()
        if key != "record_sha256"
    }

    expected_hash = _sha256(unsigned_record)

    return supplied_hash == expected_hash


def authorize_tool(tool_name: str, approved: bool) -> dict:
    if not approved:
        return {
            "decision": "deny",
            "tool": tool_name,
            "reason": "human approval required",
        }

    return {
        "decision": "allow",
        "tool": tool_name,
        "reason": "human approved",
    }


def make_tool_authorization_record(tool_name: str, approved: bool) -> dict:
    record = {
        "authorization_id": str(uuid.uuid4()),
        "tool": tool_name,
        "authorization": authorize_tool(tool_name, approved),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    record["record_sha256"] = _sha256(record)

    return record


def run_governed_tool(tool_name: str, authorization_record: dict) -> dict:
    if not verify_record(authorization_record):
        return {
            "tool": tool_name,
            "status": "denied",
            "reason": "invalid authorization record",
        }

    authorization = authorization_record.get("authorization", {})

    if authorization.get("decision") != "allow":
        return {
            "tool": tool_name,
            "status": "denied",
            "reason": "tool not authorized",
        }

    if authorization.get("tool") != tool_name:
        return {
            "tool": tool_name,
            "status": "denied",
            "reason": "authorization does not match tool",
        }

    return {
        "tool": tool_name,
        "status": "authorized",
        "authorization_id": authorization_record.get("authorization_id"),
    }


def execute_governed_tool(tool_name: str, authorization_record: dict) -> dict:
    decision = run_governed_tool(tool_name, authorization_record)

    executed_at = datetime.now(timezone.utc).isoformat()

    record = {
        "tool_execution_id": str(uuid.uuid4()),
        "tool": tool_name,
        "authorization_id": authorization_record.get("authorization_id"),
        "authorization_status": decision["status"],
        "executed_at": executed_at,
    }

    if decision["status"] != "authorized":
        record["status"] = "denied"
        record["reason"] = decision.get("reason")
    else:
        record["status"] = "executed"
        record["result"] = {
            "message": f"{tool_name} execution simulated successfully"
        }

    record["record_sha256"] = _sha256(record)

    return record


def list_current_directory(authorization_record: dict) -> dict:
    tool_name = "list_current_directory"

    decision = run_governed_tool(tool_name, authorization_record)

    executed_at = datetime.now(timezone.utc).isoformat()

    record = {
        "tool_execution_id": str(uuid.uuid4()),
        "tool": tool_name,
        "authorization_id": authorization_record.get("authorization_id"),
        "authorization_status": decision["status"],
        "executed_at": executed_at,
    }

    if decision["status"] != "authorized":
        record["status"] = "denied"
        record["reason"] = decision.get("reason")
    else:
        import os

        record["status"] = "executed"
        record["result"] = {
            "files": sorted(os.listdir(".")),
        }

    record["record_sha256"] = _sha256(record)

    return record


def run_local_agent_with_receipt(prompt: str, request_type: str = "model") -> dict:
    from app.generator import generate_receipt
    from app.verifier import verify_receipt

    execution = run_local_agent(prompt, request_type=request_type)
    bundle = generate_receipt(payload=execution)
    receipt = bundle["receipt"]
    verification = verify_receipt(receipt)

    return {
        "execution": execution,
        "receipt": receipt,
        "verification": verification,
    }


def propose_tool_action(user_request: str) -> dict:
    prompt = f"""
You are a local planning model inside a governed PFC system.

Do not execute tools.
Do not claim that any action was performed.

Return ONLY valid JSON with exactly these fields:
{{
  "tool": "list_current_directory",
  "reason": "short explanation"
}}

The only tool you are allowed to propose is:
list_current_directory

User request:
{user_request}
"""

    result = ask_ollama(prompt)

    try:
        proposal = json.loads(result["content"])
    except Exception:
        return {
            "status": "invalid_proposal",
            "raw_output": result["content"],
        }

    return {
        "status": "proposed",
        "proposal": proposal,
        "model": result["model"],
        "provider": result["provider"],
    }


ALLOWED_TOOLS = {
    "list_current_directory",
}


def validate_tool_proposal(proposal_result: dict) -> dict:
    if proposal_result.get("status") != "proposed":
        return {
            "decision": "deny",
            "reason": "no valid model proposal",
        }

    proposal = proposal_result.get("proposal", {})
    tool_name = proposal.get("tool")

    if tool_name not in ALLOWED_TOOLS:
        return {
            "decision": "deny",
            "tool": tool_name,
            "reason": "tool is not in PFC allowlist",
        }

    return {
        "decision": "allow",
        "tool": tool_name,
        "reason": "tool is permitted for authorization review",
    }


def prepare_governed_action(user_request: str) -> dict:
    proposal = propose_tool_action(user_request)
    validation = validate_tool_proposal(proposal)

    if validation["decision"] != "allow":
        return {
            "status": "denied_by_pfc",
            "proposal": proposal,
            "validation": validation,
        }

    return {
        "status": "awaiting_human_approval",
        "proposal": proposal,
        "validation": validation,
        "tool": validation["tool"],
    }


def complete_governed_action(prepared_action: dict, approved: bool) -> dict:
    from app.generator import generate_receipt
    from app.verifier import verify_receipt

    if prepared_action.get("status") != "awaiting_human_approval":
        return {
            "status": "denied",
            "reason": "action is not awaiting human approval",
        }

    tool_name = prepared_action.get("tool")

    authorization_record = make_bound_tool_authorization_record(
        prepared_action,
        approved,
    )

    binding = verify_bound_authorization(
        prepared_action,
        authorization_record,
    )

    if binding["decision"] != "allow":
        execution = {
            "tool": tool_name,
            "status": "denied",
            "reason": binding["reason"],
        }
    elif tool_name == "list_current_directory":
        execution = list_current_directory(authorization_record)
    else:
        execution = {
            "tool": tool_name,
            "status": "denied",
            "reason": "no execution handler registered",
        }

    receipt_bundle = generate_receipt(
        payload={
            "prepared_action": prepared_action,
            "authorization": authorization_record,
            "execution": execution,
        }
    )

    receipt = receipt_bundle["receipt"]

    return {
        "status": execution["status"],
        "prepared_action": prepared_action,
        "authorization": authorization_record,
        "execution": execution,
        "receipt": receipt,
        "verification": verify_receipt(receipt),
    }


def proposal_hash(prepared_action: dict) -> str:
    proposal = prepared_action.get("proposal", {})
    return _sha256(proposal)


def make_bound_tool_authorization_record(
    prepared_action: dict,
    approved: bool,
) -> dict:
    tool_name = prepared_action.get("tool")

    record = {
        "authorization_id": str(uuid.uuid4()),
        "tool": tool_name,
        "proposal_sha256": proposal_hash(prepared_action),
        "authorization": authorize_tool(tool_name, approved),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    record["record_sha256"] = _sha256(record)

    return record


def verify_bound_authorization(
    prepared_action: dict,
    authorization_record: dict,
) -> dict:
    if not verify_record(authorization_record):
        return {
            "decision": "deny",
            "reason": "invalid authorization record",
        }

    expected = proposal_hash(prepared_action)
    supplied = authorization_record.get("proposal_sha256")

    if supplied != expected:
        return {
            "decision": "deny",
            "reason": "authorization does not match proposal",
        }

    if authorization_record.get("tool") != prepared_action.get("tool"):
        return {
            "decision": "deny",
            "reason": "authorization does not match tool",
        }

    return {
        "decision": "allow",
        "reason": "authorization matches proposal",
    }
