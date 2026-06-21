import re
from typing import Any, Dict, List, Tuple

REQUIRED_FIELDS = {"receiptId", "timestamp", "payloadHash", "signature"}
PAYLOAD_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


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

    valid = all(v == "PASS" for v in checks.values())
    return {"valid": valid, "checks": checks, "errors": errors}
