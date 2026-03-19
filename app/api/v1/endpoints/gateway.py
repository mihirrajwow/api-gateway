"""
Simulated downstream gateway routes.

These endpoints are protected by GatewayMiddleware (X-API-Key + rate limiting).
They represent the "proxied" API surface that clients consume using their API keys.
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/gateway", tags=["Gateway (API-Key Protected)"])


class EchoPayload(BaseModel):
    message: str


# ------------------------------------------------------------------ #
# Simple health-style ping (rate-limited)
# ------------------------------------------------------------------ #
@router.get("/ping", summary="Authenticated ping — verifies your API key works")
async def ping(request: Request):
    return {
        "pong": True,
        "user_id": getattr(request.state, "user_id", None),
        "rate_limit_remaining": getattr(request.state, "rate_info", {}).get("remaining"),
    }


# ------------------------------------------------------------------ #
# Echo endpoint — demonstrates request validation
# ------------------------------------------------------------------ #
@router.post("/echo", summary="Echo back a message (rate-limited)")
async def echo(payload: EchoPayload, request: Request):
    return {
        "echo": payload.message,
        "user_id": getattr(request.state, "user_id", None),
        "rate_info": getattr(request.state, "rate_info", {}),
    }


# ------------------------------------------------------------------ #
# Resource simulation endpoints
# ------------------------------------------------------------------ #
@router.get("/data", summary="Simulated data fetch (rate-limited)")
async def get_data(request: Request):
    return {
        "data": [
            {"id": 1, "value": "alpha"},
            {"id": 2, "value": "beta"},
            {"id": 3, "value": "gamma"},
        ],
        "user_id": getattr(request.state, "user_id", None),
    }


@router.get("/data/{item_id}", summary="Fetch a single item (per-endpoint rate limit)")
async def get_item(item_id: int, request: Request):
    return {
        "id": item_id,
        "value": f"item_{item_id}",
        "user_id": getattr(request.state, "user_id", None),
    }
