import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.api_v1 import router as v1_router
from app.db import fetch_receipt, init_db, save_receipt
from app.generator import generate_receipt
from app.ui import INDEX_HTML
from app.verifier import verify_receipt


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PFC Receipt Verifier",
    version="0.1.0",
    description="Verify and generate PFC receipts with Ed25519 signatures. OpenAPI docs at /docs.",
    lifespan=lifespan,
)
app.include_router(v1_router)


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML


@app.get("/health")
def health():
    return {"status": "ok", "service": "pfc-verifier"}


@app.post("/verify")
async def verify(request: Request):
    data: Dict[str, Any] = await request.json()
    return verify_receipt(data)


class GenerateRequest(BaseModel):
    receiptId: Optional[str] = None
    timestamp: Optional[str] = None
    payload: Optional[Any] = None
    payloadHash: Optional[str] = None


@app.post("/generate")
def generate(req: GenerateRequest = GenerateRequest()):
    result = generate_receipt(
        receipt_id=req.receiptId,
        timestamp=req.timestamp,
        payload=req.payload,
        payload_hash=req.payloadHash,
    )
    receipt = result["receipt"]
    save_receipt(receipt, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    result["url"] = f"/r/{receipt['receiptId']}"
    return result


@app.post("/receipts")
async def store_receipt(request: Request):
    data: Dict[str, Any] = await request.json()
    receipt_id = data.get("receiptId")
    if not receipt_id:
        raise HTTPException(status_code=400, detail="receiptId is required")
    save_receipt(data, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    return {"receiptId": receipt_id, "url": f"/r/{receipt_id}"}


@app.get("/receipts/{receipt_id}")
def get_receipt(receipt_id: str):
    data = fetch_receipt(receipt_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return data


@app.get("/r/{receipt_id}", response_class=HTMLResponse)
def receipt_page(receipt_id: str):
    return INDEX_HTML


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
