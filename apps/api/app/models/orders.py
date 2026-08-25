"""Shop-scoped orders with immutable price snapshots."""
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import OrderStatus

if TYPE_CHECKING:
    from app.models.catalog import Product
    from app.models.identity import Customer
    from app.models.tenancy import Shop


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    order_number: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), default=OrderStatus.PENDING, nullable=False
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id", ondelete="SET NULL"))
    address_snapshot: Mapped[str | None] = mapped_column(Text)
    phone_snapshot: Mapped[str | None] = mapped_column(String(32))
    customer_name_snapshot: Mapped[str | None] = mapped_column(String(256))
    comment: Mapped[str | None] = mapped_column(Text)
    # Set by the client per checkout attempt; replaying the same key returns the same order.
    idempotency_key: Mapped[str | None] = mapped_column(String(64))

    shop: Mapped["Shop"] = relationship(back_populates="orders")
    customer: Mapped["Customer"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("shop_id", "order_number", name="uq_orders_shop_order_number"),
        UniqueConstraint("customer_id", "idempotency_key", name="uq_orders_customer_idempotency"),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_non_negative"),
        CheckConstraint("subtotal >= 0", name="ck_orders_subtotal_non_negative"),
        Index("ix_orders_shop_status", "shop_id", "status"),
        Index("ix_orders_shop_created", "shop_id", "created_at"),
        Index("ix_orders_customer_id", "customer_id"),
        # Customer order history is always "mine, newest first".
        Index("ix_orders_customer_created", "customer_id", "created_at"),
        # Seller order board filters by status inside one shop, newest first.
        Index("ix_orders_shop_status_created", "shop_id", "status", "created_at"),
    )


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    product_name_snapshot: Mapped[str] = mapped_column(String(256), nullable=False)
    # The list price at checkout time; kept so a receipt can show what was discounted.
    list_price_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    # The price actually charged per unit — discount already applied.
    price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product | None"] = relationship()

    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_order_items_qty_positive"),
        CheckConstraint("price_snapshot >= 0", name="ck_order_items_price_non_negative"),
        Index("ix_order_items_order_id", "order_id"),
    )
