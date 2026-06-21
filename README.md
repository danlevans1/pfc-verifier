# PFC Receipt Verifier

MVP service for verifying PFC (Prime Form Calculus) receipts.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| POST | `/verify` | Verify a PFC receipt |

## POST /verify

Accepts any JSON object and returns a validation result.

**Example request:**
```json
{
  "receiptId": "receipt-abc-123",
  "timestamp": "2026-06-21T00:00:00Z",
  "payloadHash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "signature": "deadbeef"
}
```

**Example response:**
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

### Validation rules

| Check | PASS condition |
|-------|---------------|
| `schema` | Receipt contains `receiptId`, `timestamp`, `payloadHash`, `signature` |
| `payloadHash` | Value is a 64-character lowercase hex string |
| `signature` | Value is a non-empty string |

## Running locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Running tests

```bash
pytest tests/ -v
```

## Deploy to Railway

This repo includes a `Dockerfile` and `railway.json`. Connect the repo in Railway and it will build and deploy automatically. The `PORT` environment variable is set by Railway at runtime.
