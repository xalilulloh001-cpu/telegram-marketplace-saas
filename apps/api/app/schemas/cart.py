"""Cart and favorites contracts for the customer realm.

Nothing here exposes a raw stock count, shop membership or other seller-internal state.
Totals are always server-computed — a client-supplied subtotal is never read.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemResponse(BaseModel):
    item_id: int
    product_id: int
    product_name: str
    image_url: str | None
    quantity: int
    unit_price: Decimal
    display_price: Decimal
    line_total: Decimal
    in_stock: bool
    available: bool


class CartResponse(BaseModel):
    cart_id: int | None
    shop_id: int
    items: list[CartItemResponse]
    subtotal: Decimal
    total_items: int


class FavoriteResponse(BaseModel):
    product_id: int
    shop_id: int
    product_name: str
    image_url: str | None
    price: Decimal
    discount_price: Decimal | None
    display_price: Decimal
    in_stock: bool
    is_available: bool
    created_at: datetime
