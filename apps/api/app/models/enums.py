"""Enumerations used across the schema, stored as native PostgreSQL enums."""
import enum


class ShopStatus(str, enum.Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    BLOCKED = "blocked"


class ShopMemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"


class PrincipalType(str, enum.Enum):
    """Which authentication realm a session belongs to. Realms never mix."""

    CUSTOMER = "customer"
    SELLER = "seller"
    PLATFORM_ADMIN = "platform_admin"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
