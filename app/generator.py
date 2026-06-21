import hashlib
import secrets
from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.verifier import canonical_payload


def _b64url(b: bytes) -> str:
    return urlsafe_b64encode(b).rstrip(b"=").decode()


def generate_receipt(
    receipt_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    payload_hash: Optional[str] = None,
) -> Dict[str, Any]:
    private_key = Ed25519PrivateKey.generate()

    receipt_id = receipt_id or ("receipt-" + secrets.token_hex(8))
    timestamp = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload_hash = payload_hash or hashlib.sha256(secrets.token_bytes(32)).hexdigest()

    receipt: Dict[str, Any] = {
        "receiptId": receipt_id,
        "timestamp": timestamp,
        "payloadHash": payload_hash,
        "publicKey": _b64url(private_key.public_key().public_bytes_raw()),
    }
    receipt["signature"] = _b64url(private_key.sign(canonical_payload(receipt)))

    return {
        "receipt": receipt,
        "privateKey": _b64url(private_key.private_bytes_raw()),
    }
