from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, api_keys, logs, gateway

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(api_keys.router)
api_router.include_router(logs.router)
api_router.include_router(gateway.router)
