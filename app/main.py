import os
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from app.ui import INDEX_HTML
from app.verifier import verify_receipt

app = FastAPI(title="PFC Receipt Verifier", version="0.1.0")


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
