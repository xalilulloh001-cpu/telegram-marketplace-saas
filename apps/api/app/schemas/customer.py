"""Customer-facing contracts.

Deliberately separate from the seller schemas: nothing here exposes stock counts, plan,
membership, status or other internal state. Adding a field to a seller model can never
leak it to customers by accident.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, computed_field


class CustomerShopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    logo_url: str | None


class CustomerShopDetailResponse(CustomerShopResponse):
    contact_phone: str | None
    contact_email: str | None
    address_line: str | None
    city: str | None


class CustomerCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    parent_id: int | None


class CustomerProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str


class CustomerProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    price: Decimal
    discount_price: Decimal | None
    category_id: int | None
    image_url: str | None = None
    in_stock: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_price(self) -> Decimal:
        """What the customer actually pays — the discount when set, otherwise the price."""
        return self.discount_price if self.discount_price is not None else self.price


class CustomerProductDetailResponse(CustomerProductResponse):
    description: str | None
    images: list[CustomerProductImageResponse] = []
    category: CustomerCategoryResponse | None = None
    created_at: datetime
