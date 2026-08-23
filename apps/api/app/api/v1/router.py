"""Aggregates all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import admin_auth, auth, health
from app.api.v1.seller import categories as seller_categories
from app.api.v1.seller import products as seller_products
from app.api.v1.seller import shop as seller_shop

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(admin_auth.router)
api_router.include_router(seller_shop.router)
api_router.include_router(seller_categories.router)
api_router.include_router(seller_products.router)
