"""Global identity: users, customers, addresses, platform admins."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.commerce import Cart, Favorite
    from app.models.orders import Order
    from app.models.tenancy import ShopMember


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    username: Mapped[str | None] = mapped_column(String(64))
    phone: Mapped[str | None] = mapped_column(String(32))

    customer: Mapped["Customer | None"] = relationship(back_populates="user", uselist=False)
    shop_members: Mapped[list["ShopMember"]] = relationship(back_populates="user")
    platform_admin: Mapped["PlatformAdmin | None"] = relationship(
        back_populates="user", uselist=False
    )


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    default_address_id: Mapped[int | None] = mapped_column(
        ForeignKey("addresses.id", ondelete="SET NULL", use_alter=True, name="fk_customer_address")
    )

    user: Mapped["User"] = relationship(back_populates="customer")
    addresses: Mapped[list["Address"]] = relationship(
        back_populates="customer",
        foreign_keys="Address.customer_id",
        cascade="all, delete-orphan",
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")
    carts: Mapped[list["Cart"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class Address(Base, TimestampMixin):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str | None] = mapped_column(String(64))
    full_address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    customer: Mapped["Customer"] = relationship(
        back_populates="addresses", foreign_keys=[customer_id]
    )

    __table_args__ = (Index("ix_addresses_customer_id", "customer_id"),)


class PlatformAdmin(Base, TimestampMixin):
    __tablename__ = "platform_admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="platform_admin")
