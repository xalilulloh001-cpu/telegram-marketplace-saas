"""Aggregates all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import admin_auth, auth, health
from app.api.v1.customer import cart as customer_cart
from app.api.v1.customer import catalog as customer_catalog
from app.api.v1.customer import orders as customer_orders
from app.api.v1.seller import categories as seller_categories
from app.api.v1.seller import orders as seller_orders
from app.api.v1.seller import products as seller_products
from app.api.v1.seller import shop as seller_shop

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(admin_auth.router)
api_router.include_router(customer_catalog.router)
api_router.include_router(customer_cart.cart_router)
api_router.include_router(customer_cart.favorites_router)
api_router.include_router(customer_orders.checkout_router)
api_router.include_router(customer_orders.orders_router)
api_router.include_router(seller_shop.router)
api_router.include_router(seller_categories.router)
api_router.include_router(seller_products.router)
api_router.include_router(seller_orders.router)
