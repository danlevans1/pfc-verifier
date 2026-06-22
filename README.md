# PFC Receipt Verifier

Service for verifying PFC (Prime Form Calculus) receipts, including Ed25519 cryptographic signature verification.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| POST | `/verify` | Verify a PFC receipt |

## POST /verify

### Legacy receipt (no cryptographic verification)

Omit `publicKey` to skip Ed25519 verification. Existing consumers are unaffected.

```json
{
  "receiptId": "receipt-abc-123",
  "timestamp": "2026-06-21T00:00:00Z",
  "payloadHash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "signature": "any-non-empty-string"
}
```

Response:
```json
{
  "valid": true,
  "checks": {
    "schema": "PASS",
    "payloadHash": "PASS",
    "signature": "PASS"
  },
  "errors": []
}
```

### Signed receipt (Ed25519 verification)

Include `publicKey` to trigger cryptographic verification.

```json
{
  "receiptId": "receipt-v2-001",
  "timestamp": "2026-06-21T00:00:00Z",
  "payloadHash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "publicKey": "<base64url-encoded Ed25519 public key>",
  "signature": "<base64url-encoded Ed25519 signature>"
}
```

Response:
```json
{
  "valid": true,
  "checks": {
    "schema": "PASS",
    "payloadHash": "PASS",
    "signature": "PASS",
    "cryptographicSignature": "PASS"
  },
  "errors": []
}
```

### Validation rules

| Check | PASS condition |
|-------|---------------|
| `schema` | Receipt contains `receiptId`, `timestamp`, `payloadHash`, `signature` |
| `payloadHash` | Value is a 64-character lowercase hex string |
| `signature` | Value is a non-empty string |
| `cryptographicSignature` | Only present when `publicKey` is included. Ed25519 signature verifies against the canonical payload. |

### Canonical payload

The signed message is the compact JSON of exactly these three fields, keys sorted alphabetically:

```
{"payloadHash":"<value>","receiptId":"<value>","timestamp":"<value>"}
```

All values taken verbatim from the receipt. No whitespace.

## Working with Ed25519 receipts

### Generate a keypair

```python
from base64 import urlsafe_b64encode
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def b64url(b: bytes) -> str:
    return urlsafe_b64encode(b).rstrip(b"=").decode()

private_key = Ed25519PrivateKey.generate()
public_key  = private_key.public_key()

print("private:", b64url(private_key.private_bytes_raw()))
print("public: ", b64url(public_key.public_bytes_raw()))
```

Store the private key securely (never include it in a receipt). Distribute the public key.

### Sign a receipt

```python
import json
from base64 import urlsafe_b64encode
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def b64url(b: bytes) -> str:
    return urlsafe_b64encode(b).rstrip(b"=").decode()

def canonical_payload(receipt: dict) -> bytes:
    fields = {k: receipt[k] for k in ("payloadHash", "receiptId", "timestamp")}
    return json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()

# Load your private key (from secure storage)
private_key = Ed25519PrivateKey.generate()  # replace with your actual key

receipt = {
    "receiptId":   "receipt-v2-001",
    "timestamp":   "2026-06-21T00:00:00Z",
    "payloadHash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "publicKey":   b64url(private_key.public_key().public_bytes_raw()),
}
receipt["signature"] = b64url(private_key.sign(canonical_payload(receipt)))
print(json.dumps(receipt, indent=2))
```

### Verify a receipt

```bash
curl -s -X POST https://<your-railway-url>/verify \
  -H "Content-Type: application/json" \
  -d @receipt.json | jq .
```

Or in Python:

```python
import httpx, json

with open("receipt.json") as f:
    receipt = json.load(f)

r = httpx.post("https://<your-railway-url>/verify", json=receipt)
print(r.json())
```

## Developer API (v1)

All v1 endpoints are versioned under `/api/v1`, return JSON, and are fully documented in the interactive Swagger UI at `/docs`.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/receipts/generate` | Generate, sign, and store a receipt |
| `POST` | `/api/v1/receipts/verify` | Verify a receipt JSON |
| `GET` | `/api/v1/receipts/{receiptId}` | Look up a stored receipt + verification result |

### curl examples

**Generate a signed receipt**

```bash
curl -s -X POST https://<your-railway-url>/api/v1/receipts/generate \
  -H "Content-Type: application/json" \
  -d '{"payload": {"agent": "alpha", "action": "transfer"}}' | jq .
```

**Verify a receipt**

```bash
curl -s -X POST https://<your-railway-url>/api/v1/receipts/verify \
  -H "Content-Type: application/json" \
  -d @receipt.json | jq .
```

**Look up a stored receipt**

```bash
curl -s https://<your-railway-url>/api/v1/receipts/receipt-abc123 | jq .
```

### Python example

```python
import requests

BASE = "https://<your-railway-url>"

# 1. Generate a signed receipt
resp = requests.post(
    f"{BASE}/api/v1/receipts/generate",
    json={"payload": {"agent": "alpha", "action": "transfer"}},
)
data = resp.json()
receipt    = data["receipt"]
private_key = data["privateKey"]   # store securely
share_url  = BASE + data["url"]    # e.g. https://.../r/receipt-abc123

# 2. Verify the receipt
resp = requests.post(f"{BASE}/api/v1/receipts/verify", json=receipt)
print(resp.json())
# {"valid": True, "checks": {"schema": "PASS", ..., "cryptographicSignature": "PASS"}, "errors": []}

# 3. Look up a stored receipt by ID
resp = requests.get(f"{BASE}/api/v1/receipts/{receipt['receiptId']}")
print(resp.json())
# {"receipt": {...}, "verification": {"valid": True, "checks": {...}, "errors": []}}
```

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Running tests

```bash
pytest tests/ -v
```

## Deploy to Railway

This repo includes a `Dockerfile` and `railway.json`. Connect the repo in Railway and it deploys automatically. `PORT` is set by Railway at runtime.
