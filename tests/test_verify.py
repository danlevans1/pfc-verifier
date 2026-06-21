import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_RECEIPT = {
    "receiptId": "receipt-abc-123",
    "timestamp": "2026-06-21T00:00:00Z",
    "payloadHash": "a" * 64,
    "signature": "deadbeef",
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "pfc-verifier"}


def test_valid_receipt():
    r = client.post("/verify", json=VALID_RECEIPT)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["checks"]["schema"] == "PASS"
    assert body["checks"]["payloadHash"] == "PASS"
    assert body["checks"]["signature"] == "PASS"
    assert body["errors"] == []


def test_missing_required_field():
    receipt = {k: v for k, v in VALID_RECEIPT.items() if k != "signature"}
    r = client.post("/verify", json=receipt)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False
    assert body["checks"]["schema"] == "FAIL"
    assert any("signature" in e for e in body["errors"])


def test_invalid_payload_hash():
    receipt = {**VALID_RECEIPT, "payloadHash": "not-a-valid-hash"}
    r = client.post("/verify", json=receipt)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False
    assert body["checks"]["schema"] == "PASS"
    assert body["checks"]["payloadHash"] == "FAIL"
    assert any("payloadHash" in e for e in body["errors"])


def test_empty_signature():
    receipt = {**VALID_RECEIPT, "signature": ""}
    r = client.post("/verify", json=receipt)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False
    assert body["checks"]["schema"] == "PASS"
    assert body["checks"]["signature"] == "FAIL"
    assert any("signature" in e for e in body["errors"])
