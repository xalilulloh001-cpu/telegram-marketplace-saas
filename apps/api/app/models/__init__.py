"""All models are imported here so Alembic autogenerate sees the full metadata."""
from app.models.catalog import Category, Product, ProductImage
from app.models.commerce import Cart, CartItem, Favorite
from app.models.enums import OrderStatus, ShopMemberRole, ShopStatus, SubscriptionStatus
from app.models.identity import Address, Customer, PlatformAdmin, User
from app.models.orders import Order, OrderItem
from app.models.tenancy import Plan, Shop, ShopMember, Subscription

__all__ = [
    "Address",
    "Cart",
    "CartItem",
    "Category",
    "Customer",
    "Favorite",
    "Order",
    "OrderItem",
    "OrderStatus",
    "PlatformAdmin",
    "Plan",
    "Product",
    "ProductImage",
    "Shop",
    "ShopMember",
    "ShopMemberRole",
    "ShopStatus",
    "Subscription",
    "SubscriptionStatus",
    "User",
]
