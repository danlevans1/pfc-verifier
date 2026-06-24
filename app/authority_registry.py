from typing import Any, Dict, List, Optional

REGISTRY: Dict[str, Dict[str, Any]] = {
    "pfc-main": {
        "authorityId": "pfc-main",
        "name": "Prime Form Calculus",
        "website": "https://primeformcalculus.com",
        "trusted": True,
    },
}


def list_authorities() -> List[Dict[str, Any]]:
    return list(REGISTRY.values())


def get_authority(authority_id: str) -> Optional[Dict[str, Any]]:
    return REGISTRY.get(authority_id)


def resolve_status(authority: Dict[str, Any]) -> str:
    """Map an embedded authority block to a trust-status string."""
    entry = REGISTRY.get(authority.get("authorityId", ""))
    if entry is None:
        return "unknown"
    return "trusted" if entry.get("trusted") else "untrusted"
