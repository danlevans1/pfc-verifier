import hashlib
import json
from base64 import urlsafe_b64encode

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

import app.db as _db
from app.main import app
from app.verifier import canonical_payload

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(_db, "DB_PATH", str(tmp_path / "test.db"))
    _db.init_db()

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


# ── UI tests ──────────────────────────────────────────────────────────────────

def test_root_returns_200():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_root_contains_title():
    r = client.get("/")
    assert "PFC Verifier" in r.text


def test_root_has_dynamic_checks_area():
    """Page must contain the checks container that JS populates dynamically."""
    r = client.get("/")
    assert 'id="checks"' in r.text


def test_root_has_verified_at_element():
    """Page must contain the timestamp element populated after each verify call."""
    r = client.get("/")
    assert 'id="verified-at"' in r.text


def test_root_has_raw_json_panel():
    """Page must contain the raw JSON debug panel."""
    r = client.get("/")
    assert 'id="raw-json-panel"' in r.text
    assert 'id="raw-json"' in r.text


# ── Generator endpoint tests ──────────────────────────────────────────────────

def test_generate_returns_signed_receipt():
    r = client.post("/generate", json={})
    assert r.status_code == 200
    body = r.json()
    assert "receipt" in body
    assert "privateKey" in body
    for field in ("receiptId", "timestamp", "payloadHash", "publicKey", "signature"):
        assert field in body["receipt"]


def test_generate_uses_provided_fields():
    r = client.post("/generate", json={
        "receiptId": "my-receipt",
        "timestamp": "2026-06-21T00:00:00Z",
        "payloadHash": "a" * 64,
    })
    receipt = r.json()["receipt"]
    assert receipt["receiptId"] == "my-receipt"
    assert receipt["timestamp"] == "2026-06-21T00:00:00Z"
    assert receipt["payloadHash"] == "a" * 64


def test_generated_receipt_passes_verification():
    receipt = client.post("/generate", json={}).json()["receipt"]
    body = client.post("/verify", json=receipt).json()
    assert body["valid"] is True
    assert body["checks"]["cryptographicSignature"] == "PASS"


# ── Generator UI tests ────────────────────────────────────────────────────────

def test_root_has_generate_tab():
    r = client.get("/")
    assert 'data-tab="generate"' in r.text


def test_root_has_generate_btn():
    r = client.get("/")
    assert 'id="generate-btn"' in r.text


def test_root_has_generated_receipt_element():
    r = client.get("/")
    assert 'id="generated-receipt"' in r.text
    assert 'id="generator"' in r.text


# ── V5.1: payload JSON generation tests ──────────────────────────────────────

def test_generate_with_payload_json():
    r = client.post("/generate", json={"payload": {"agent": "alpha", "action": "transfer"}})
    assert r.status_code == 200
    ph = r.json()["receipt"]["payloadHash"]
    assert len(ph) == 64
    assert all(c in "0123456789abcdef" for c in ph)


def test_generate_payload_hash_is_sha256_of_canonical_json():
    payload = {"z": 1, "a": 2}
    r = client.post("/generate", json={"payload": payload})
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert r.json()["receipt"]["payloadHash"] == expected


def test_root_has_payload_json_editor():
    r = client.get("/")
    assert 'id="gen-payload"' in r.text


def test_root_has_verify_generated_btn():
    r = client.get("/")
    assert 'id="verify-generated-btn"' in r.text


# ── V6: registry & shareable URL tests ───────────────────────────────────────

def test_store_and_fetch_receipt():
    r = client.post("/receipts", json=VALID_RECEIPT)
    assert r.status_code == 200
    body = r.json()
    assert body["receiptId"] == VALID_RECEIPT["receiptId"]
    assert body["url"] == f"/r/{VALID_RECEIPT['receiptId']}"

    r2 = client.get(f"/receipts/{VALID_RECEIPT['receiptId']}")
    assert r2.status_code == 200
    assert r2.json()["receiptId"] == VALID_RECEIPT["receiptId"]


def test_receipt_not_found():
    r = client.get("/receipts/does-not-exist")
    assert r.status_code == 404


def test_generate_auto_stores_receipt():
    body = client.post("/generate", json={}).json()
    receipt_id = body["receipt"]["receiptId"]
    r = client.get(f"/receipts/{receipt_id}")
    assert r.status_code == 200
    assert r.json()["receiptId"] == receipt_id


def test_generate_returns_url():
    body = client.post("/generate", json={}).json()
    assert "url" in body
    assert body["url"] == f"/r/{body['receipt']['receiptId']}"


def test_receipt_page_returns_html():
    r = client.get(f"/r/{VALID_RECEIPT['receiptId']}")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "PFC Verifier" in r.text


def test_root_has_share_url_element():
    r = client.get("/")
    assert 'id="share-url"' in r.text


def test_root_has_copy_url_btn():
    r = client.get("/")
    assert 'id="copy-url-btn"' in r.text


def test_generate_url_rendered_in_ui():
    """Generated receipt URL is /r/{id} and the page labels it as Shareable Verification URL."""
    body = client.post("/generate", json={}).json()
    assert body["url"] == f"/r/{body['receipt']['receiptId']}"

    page = client.get("/").text
    assert 'id="share-url"' in page
    assert "Shareable Verification URL" in page


# ── V7: Developer API v1 tests ────────────────────────────────────────────────

def test_api_generate_returns_receipt_and_url():
    r = client.post("/api/v1/receipts/generate", json={})
    assert r.status_code == 200
    body = r.json()
    assert "receipt" in body
    assert "privateKey" in body
    assert "url" in body
    assert body["url"].startswith("/r/")
    for field in ("receiptId", "timestamp", "payloadHash", "publicKey", "signature"):
        assert field in body["receipt"]


def test_api_generate_with_payload():
    r = client.post(
        "/api/v1/receipts/generate",
        json={"payload": {"agent": "beta", "action": "log"}},
    )
    assert r.status_code == 200
    ph = r.json()["receipt"]["payloadHash"]
    assert len(ph) == 64
    assert all(c in "0123456789abcdef" for c in ph)


def test_api_generate_stores_receipt():
    body = client.post("/api/v1/receipts/generate", json={}).json()
    receipt_id = body["receipt"]["receiptId"]
    r = client.get(f"/api/v1/receipts/{receipt_id}")
    assert r.status_code == 200
    assert r.json()["receipt"]["receiptId"] == receipt_id


def test_api_verify_valid_receipt():
    receipt = client.post("/api/v1/receipts/generate", json={}).json()["receipt"]
    r = client.post("/api/v1/receipts/verify", json=receipt)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["checks"]["cryptographicSignature"] == "PASS"
    assert body["errors"] == []


def test_api_verify_invalid_receipt():
    r = client.post(
        "/api/v1/receipts/verify",
        json={
            "receiptId": "x",
            "timestamp": "2026-06-22T00:00:00Z",
            "payloadHash": "not-valid",
            "signature": "abc",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False
    assert body["checks"]["payloadHash"] == "FAIL"


def test_api_lookup_returns_receipt_and_verification():
    gen = client.post("/api/v1/receipts/generate", json={}).json()
    receipt_id = gen["receipt"]["receiptId"]
    r = client.get(f"/api/v1/receipts/{receipt_id}")
    assert r.status_code == 200
    body = r.json()
    assert "receipt" in body
    assert "verification" in body
    assert body["verification"]["valid"] is True
    assert body["verification"]["checks"]["cryptographicSignature"] == "PASS"


def test_api_lookup_not_found():
    r = client.get("/api/v1/receipts/no-such-receipt")
    assert r.status_code == 404


# ── V8: authority identity layer tests ───────────────────────────────────────

def test_authority_in_generated_receipt():
    body = client.post("/generate", json={}).json()
    auth = body["receipt"]["authority"]
    assert auth["name"] == "Prime Form Calculus"
    assert auth["authorityId"] == "pfc-main"
    assert auth["website"] == "https://primeformcalculus.com"


def test_authority_passed_through_in_verify_response():
    receipt = client.post("/generate", json={}).json()["receipt"]
    body = client.post("/verify", json=receipt).json()
    assert body["valid"] is True
    assert body["authority"]["name"] == "Prime Form Calculus"


def test_legacy_receipt_without_authority_unaffected():
    body = client.post("/verify", json=VALID_RECEIPT).json()
    assert body["valid"] is True
    assert "authority" not in body


def test_api_generate_includes_authority():
    body = client.post("/api/v1/receipts/generate", json={}).json()
    auth = body["receipt"]["authority"]
    assert auth["authorityId"] == "pfc-main"
    assert auth["website"] == "https://primeformcalculus.com"


def test_root_has_authority_section():
    r = client.get("/")
    assert 'id="authority-section"' in r.text


# ── V9: authority registry tests ──────────────────────────────────────────────

def test_authority_registry_list():
    r = client.get("/api/v1/authorities")
    assert r.status_code == 200
    entries = r.json()
    assert isinstance(entries, list)
    assert any(a["authorityId"] == "pfc-main" for a in entries)
    assert any(a["trusted"] is True for a in entries)


def test_authority_registry_get_known():
    r = client.get("/api/v1/authorities/pfc-main")
    assert r.status_code == 200
    body = r.json()
    assert body["authorityId"] == "pfc-main"
    assert body["name"] == "Prime Form Calculus"
    assert body["trusted"] is True


def test_authority_registry_get_unknown():
    r = client.get("/api/v1/authorities/no-such-authority")
    assert r.status_code == 404


def test_known_authority_resolves_trusted():
    receipt = client.post("/generate", json={}).json()["receipt"]
    body = client.post("/verify", json=receipt).json()
    assert body["authority"]["status"] == "trusted"


def test_unknown_authority_resolves_unknown():
    receipt = client.post("/generate", json={}).json()["receipt"]
    receipt["authority"]["authorityId"] = "unregistered-org"
    body = client.post("/verify", json=receipt).json()
    assert body["authority"]["status"] == "unknown"
