"""Catalog contracts. shop_id is never accepted from the client — it comes from the session."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    parent_id: int | None = None
    is_active: bool = True
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    parent_id: int | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    name: str
    slug: str
    parent_id: int | None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str | None = None
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    discount_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    category_id: int | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def discount_not_above_price(self) -> "ProductBase":
        if self.discount_price is not None and self.discount_price > self.price:
            raise ValueError("discount_price cannot exceed price")
        return self


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    discount_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    category_id: int | None = None
    is_active: bool | None = None


class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    url: str
    sort_order: int


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    category_id: int | None
    name: str
    slug: str
    description: str | None
    price: Decimal
    discount_price: Decimal | None
    stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductDetailResponse(ProductResponse):
    images: list[ProductImageResponse] = []


class ProductImageUpdate(BaseModel):
    sort_order: int = Field(ge=0)


PRODUCT_SORTS = ("newest", "oldest", "price_asc", "price_desc", "name_asc", "name_desc")


class ProductSort(BaseModel):
    value: str = "newest"

    @field_validator("value")
    @classmethod
    def known_sort(cls, v: str) -> str:
        if v not in PRODUCT_SORTS:
            raise ValueError("unsupported sort")
        return v
