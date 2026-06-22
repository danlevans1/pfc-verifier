from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import fetch_receipt, save_receipt
from app.generator import generate_receipt
from app.verifier import verify_receipt

router = APIRouter(prefix="/api/v1", tags=["API v1"])


# ── Request models ────────────────────────────────────────────────────────────

class ApiGenerateRequest(BaseModel):
    receiptId: Optional[str] = Field(
        None, description="Custom receipt ID — auto-generated if omitted"
    )
    timestamp: Optional[str] = Field(
        None, description="ISO 8601 timestamp — defaults to now"
    )
    payload: Optional[Any] = Field(
        None,
        description="Arbitrary JSON payload; SHA-256 of its canonical form becomes payloadHash",
    )
    payloadHash: Optional[str] = Field(
        None,
        description="Explicit 64-char lowercase hex payloadHash; ignored when payload is given",
    )


class ApiVerifyRequest(BaseModel):
    model_config = {"extra": "allow"}

    receiptId: str = Field(..., description="Unique receipt identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    payloadHash: str = Field(..., description="64-char lowercase hex SHA-256 hash")
    signature: str = Field(..., description="Base64url-encoded Ed25519 signature")
    publicKey: Optional[str] = Field(
        None,
        description="Base64url-encoded Ed25519 public key — enables cryptographic verification",
    )


# ── Response models ───────────────────────────────────────────────────────────

class VerificationResult(BaseModel):
    valid: bool = Field(..., description="True only when every check passes")
    checks: Dict[str, str] = Field(
        ..., description="Per-check result: PASS or FAIL"
    )
    errors: List[str] = Field(..., description="Human-readable error messages")


class ApiGenerateResponse(BaseModel):
    receipt: Dict[str, Any] = Field(..., description="The fully signed receipt")
    privateKey: str = Field(
        ..., description="Base64url-encoded Ed25519 private key — store securely, never share"
    )
    url: str = Field(..., description="Shareable verification URL path, e.g. /r/{receiptId}")


class ApiLookupResponse(BaseModel):
    receipt: Dict[str, Any] = Field(..., description="The stored receipt")
    verification: VerificationResult = Field(
        ..., description="Current verification result for this receipt"
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/receipts/generate",
    response_model=ApiGenerateResponse,
    summary="Generate a signed receipt",
    description=(
        "Creates a fresh Ed25519 keypair, builds a receipt from the supplied fields "
        "(auto-generating any that are omitted), signs it, stores it, and returns a "
        "shareable verification URL."
    ),
)
def api_generate(req: ApiGenerateRequest = ApiGenerateRequest()) -> ApiGenerateResponse:
    result = generate_receipt(
        receipt_id=req.receiptId,
        timestamp=req.timestamp,
        payload=req.payload,
        payload_hash=req.payloadHash,
    )
    receipt = result["receipt"]
    save_receipt(receipt, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    return ApiGenerateResponse(
        receipt=receipt,
        privateKey=result["privateKey"],
        url=f"/r/{receipt['receiptId']}",
    )


@router.post(
    "/receipts/verify",
    response_model=VerificationResult,
    summary="Verify a receipt",
    description=(
        "Validates schema completeness, payloadHash format (64-char hex), and signature "
        "presence. When publicKey is included, also verifies the Ed25519 signature against "
        "the canonical payload."
    ),
)
def api_verify(req: ApiVerifyRequest) -> VerificationResult:
    data = req.model_dump(exclude_none=True)
    result = verify_receipt(data)
    return VerificationResult(**result)


@router.get(
    "/receipts/{receipt_id}",
    response_model=ApiLookupResponse,
    summary="Look up a stored receipt",
    description="Returns the stored receipt and its current verification result. 404 if not found.",
)
def api_lookup(receipt_id: str) -> ApiLookupResponse:
    receipt = fetch_receipt(receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    verification = verify_receipt(receipt)
    return ApiLookupResponse(
        receipt=receipt,
        verification=VerificationResult(**verification),
    )
