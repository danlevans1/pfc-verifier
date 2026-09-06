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
