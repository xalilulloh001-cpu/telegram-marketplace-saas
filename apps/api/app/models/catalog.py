"""Shop-scoped catalog: categories, products, product images."""
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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

if TYPE_CHECKING:
    from app.models.tenancy import Shop


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    shop: Mapped["Shop"] = relationship(back_populates="categories")
    parent: Mapped["Category | None"] = relationship(remote_side="Category.id")
    products: Mapped[list["Product"]] = relationship(back_populates="category")

    __table_args__ = (
        Index("ix_categories_shop_parent", "shop_id", "parent_id"),
        Index("ix_categories_shop_id", "shop_id"),
        UniqueConstraint("shop_id", "parent_id", "name", name="uq_categories_shop_parent_name"),
        UniqueConstraint("shop_id", "slug", name="uq_categories_shop_slug"),
    )


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    shop: Mapped["Shop"] = relationship(back_populates="products")
    category: Mapped["Category | None"] = relationship(back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
        CheckConstraint(
            "discount_price IS NULL OR (discount_price >= 0 AND discount_price <= price)",
            name="ck_products_discount_valid",
        ),
        CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
        UniqueConstraint("shop_id", "slug", name="uq_products_shop_slug"),
        Index("ix_products_shop_category", "shop_id", "category_id"),
        Index("ix_products_shop_active", "shop_id", "is_active"),
        Index("ix_products_shop_id", "shop_id"),
    )


class ProductImage(Base, TimestampMixin):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="images")

    __table_args__ = (
        Index("ix_product_images_product_id", "product_id"),
        Index("ix_product_images_shop_id", "shop_id"),
    )
