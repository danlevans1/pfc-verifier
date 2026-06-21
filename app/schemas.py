from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class VerifyRequest(BaseModel):
    model_config = {"extra": "allow"}


class CheckResults(BaseModel):
    schema_check: str
    payloadHash: str
    signature: str

    class Config:
        fields = {"schema_check": "schema"}


class VerifyResponse(BaseModel):
    valid: bool
    checks: Dict[str, str]
    errors: List[str]
