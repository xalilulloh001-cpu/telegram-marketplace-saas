"""Enumerations used across the schema, stored as native PostgreSQL enums."""
import enum


class ShopStatus(str, enum.Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    BLOCKED = "blocked"


class ShopMemberRole(str, enum.Enum):
    OWNER = "owner"
    MANAGER = "manager"


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
