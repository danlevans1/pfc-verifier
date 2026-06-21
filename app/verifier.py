import json
import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any, Dict, List, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

REQUIRED_FIELDS = {"receiptId", "timestamp", "payloadHash", "signature"}
PAYLOAD_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def canonical_payload(data: Dict[str, Any]) -> bytes:
    """Deterministic message that is signed: compact JSON of core fields, keys sorted."""
    fields = {k: data[k] for k in ("payloadHash", "receiptId", "timestamp")}
    return json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()


def b64url_decode(s: str) -> bytes:
    padding = (4 - len(s) % 4) % 4
    return urlsafe_b64decode(s + "=" * padding)


def _verify_crypto(data: Dict[str, Any]) -> Tuple[str, List[str]]:
    try:
        pk_bytes = b64url_decode(data["publicKey"])
        public_key = Ed25519PublicKey.from_public_bytes(pk_bytes)
    except Exception:
        return "FAIL", ["publicKey is not a valid Ed25519 public key"]

    try:
        sig_bytes = b64url_decode(data["signature"])
    except Exception:
        return "FAIL", ["signature is not valid base64url"]

    try:
        public_key.verify(sig_bytes, canonical_payload(data))
        return "PASS", []
    except InvalidSignature:
        return "FAIL", ["signature does not verify against the canonical receipt payload"]


def verify_receipt(data: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    checks: Dict[str, str] = {
        "schema": "FAIL",
        "payloadHash": "FAIL",
        "signature": "FAIL",
    }

    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        for field in sorted(missing):
            errors.append(f"Missing required field: {field}")
        return {"valid": False, "checks": checks, "errors": errors}

    checks["schema"] = "PASS"

    payload_hash = data.get("payloadHash", "")
    if isinstance(payload_hash, str) and PAYLOAD_HASH_RE.match(payload_hash):
        checks["payloadHash"] = "PASS"
    else:
        errors.append("payloadHash must be a 64-character lowercase hex string")

    sig = data.get("signature", "")
    if sig and isinstance(sig, str):
        checks["signature"] = "PASS"
    else:
        errors.append("signature must be a non-empty string")

    if "publicKey" in data:
        result, crypto_errors = _verify_crypto(data)
        checks["cryptographicSignature"] = result
        errors.extend(crypto_errors)

    valid = all(v == "PASS" for v in checks.values())
    return {"valid": valid, "checks": checks, "errors": errors}
