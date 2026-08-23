"""Tenant layer: shops, shop members, plans, subscriptions."""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ShopMemberRole, ShopStatus, SubscriptionStatus

if TYPE_CHECKING:
    from app.models.catalog import Category, Product
    from app.models.identity import User
    from app.models.orders import Order


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    max_products: Mapped[int | None] = mapped_column(Integer)
    max_orders_per_month: Mapped[int | None] = mapped_column(Integer)
    features: Mapped[dict | None] = mapped_column(JSONB)

    shops: Mapped[list["Shop"]] = relationship(back_populates="plan")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Shop(Base, TimestampMixin):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    order_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    address_line: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[ShopStatus] = mapped_column(
        Enum(ShopStatus, name="shop_status"), default=ShopStatus.TRIAL, nullable=False
    )
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"))
    order_seq: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)

    plan: Mapped["Plan | None"] = relationship(back_populates="shops")
    members: Mapped[list["ShopMember"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    categories: Mapped[list["Category"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="shop")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_shops_status", "status"),)


class ShopMember(Base, TimestampMixin):
    __tablename__ = "shop_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ShopMemberRole] = mapped_column(
        Enum(ShopMemberRole, name="shop_member_role"),
        default=ShopMemberRole.OWNER,
        nullable=False,
    )

    shop: Mapped["Shop"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="shop_members")

    __table_args__ = (
        UniqueConstraint("shop_id", "user_id", name="uq_shop_members_shop_user"),
        Index("ix_shop_members_user_id", "user_id"),
    )


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    shop: Mapped["Shop"] = relationship(back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")

    __table_args__ = (Index("ix_subscriptions_shop_id", "shop_id"),)
