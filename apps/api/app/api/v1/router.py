"""Aggregates all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import admin_auth, auth, health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(admin_auth.router)
