import json
from base64 import urlsafe_b64encode

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from app.main import app
from app.verifier import canonical_payload

client = TestClient(app)

# ── helpers ──────────────────────────────────────────────────────────────────

def b64url(b: bytes) -> str:
    return urlsafe_b64encode(b).rstrip(b"=").decode()


def make_signed_receipt(private_key: Ed25519PrivateKey, **overrides) -> dict:
    pub_bytes = private_key.public_key().public_bytes_raw()
    receipt = {
        "receiptId": "receipt-v2-001",
        "timestamp": "2026-06-21T00:00:00Z",
        "payloadHash": "a" * 64,
        "publicKey": b64url(pub_bytes),
    }
    receipt["signature"] = b64url(private_key.sign(canonical_payload(receipt)))
    receipt.update(overrides)
    return receipt


# ── fixtures ─────────────────────────────────────────────────────────────────

VALID_RECEIPT = {
    "receiptId": "receipt-abc-123",
    "timestamp": "2026-06-21T00:00:00Z",
    "payloadHash": "a" * 64,
    "signature": "deadbeef",
}

# ── existing tests (must stay green) ─────────────────────────────────────────

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


# ── Ed25519 tests ─────────────────────────────────────────────────────────────

def test_valid_signed_receipt():
    key = Ed25519PrivateKey.generate()
    receipt = make_signed_receipt(key)
    r = client.post("/verify", json=receipt)
    body = r.json()
    assert body["valid"] is True
    assert body["checks"]["schema"] == "PASS"
    assert body["checks"]["payloadHash"] == "PASS"
    assert body["checks"]["signature"] == "PASS"
    assert body["checks"]["cryptographicSignature"] == "PASS"
    assert body["errors"] == []


def test_invalid_signature():
    key = Ed25519PrivateKey.generate()
    receipt = make_signed_receipt(key)
    # tamper: sign a different message
    bad_sig = b64url(key.sign(b"wrong payload"))
    receipt["signature"] = bad_sig
    r = client.post("/verify", json=receipt)
    body = r.json()
    assert body["valid"] is False
    assert body["checks"]["cryptographicSignature"] == "FAIL"
    assert any("does not verify" in e for e in body["errors"])


def test_wrong_public_key():
    key = Ed25519PrivateKey.generate()
    other_key = Ed25519PrivateKey.generate()
    receipt = make_signed_receipt(key)
    # replace publicKey with a different keypair's key
    receipt["publicKey"] = b64url(other_key.public_key().public_bytes_raw())
    r = client.post("/verify", json=receipt)
    body = r.json()
    assert body["valid"] is False
    assert body["checks"]["cryptographicSignature"] == "FAIL"


def test_malformed_public_key():
    key = Ed25519PrivateKey.generate()
    receipt = make_signed_receipt(key, publicKey="not-a-real-key!!!")
    r = client.post("/verify", json=receipt)
    body = r.json()
    assert body["valid"] is False
    assert body["checks"]["cryptographicSignature"] == "FAIL"
    assert any("publicKey" in e for e in body["errors"])


def test_malformed_signature():
    key = Ed25519PrivateKey.generate()
    # Build receipt but replace signature with garbage before signing
    pub_bytes = key.public_key().public_bytes_raw()
    receipt = {
        "receiptId": "receipt-v2-001",
        "timestamp": "2026-06-21T00:00:00Z",
        "payloadHash": "b" * 64,
        "publicKey": b64url(pub_bytes),
        "signature": "!!!not-base64!!!",
    }
    r = client.post("/verify", json=receipt)
    body = r.json()
    assert body["valid"] is False
    assert body["checks"]["cryptographicSignature"] == "FAIL"


def test_legacy_unsigned_receipt_behavior():
    """Legacy receipts without publicKey must not gain a cryptographicSignature check."""
    r = client.post("/verify", json=VALID_RECEIPT)
    body = r.json()
    assert body["valid"] is True
    assert "cryptographicSignature" not in body["checks"]
    assert set(body["checks"].keys()) == {"schema", "payloadHash", "signature"}
