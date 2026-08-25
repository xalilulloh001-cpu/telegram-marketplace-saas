"""Order contracts. Customers and sellers get different views of the same order."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import OrderStatus


class CheckoutRequest(BaseModel):
    """Everything monetary is deliberately absent: totals and prices come from the
    database at checkout time, never from the client."""

    address_id: int | None = None
    phone: str | None = Field(default=None, max_length=32)
    comment: str | None = Field(default=None, max_length=1000)
    idempotency_key: str | None = Field(default=None, max_length=64)


class OrderItemResponse(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    list_price: Decimal | None
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderResponse(BaseModel):
    id: int
    order_number: str
    shop_id: int
    shop_name: str | None = None
    status: OrderStatus
    subtotal: Decimal
    total: Decimal
    total_items: int
    created_at: datetime


class OrderDetailResponse(OrderResponse):
    items: list[OrderItemResponse]
    address_snapshot: str | None
    phone_snapshot: str | None
    customer_name_snapshot: str | None
    comment: str | None
    updated_at: datetime


class SellerOrderResponse(OrderDetailResponse):
    """Adds the counterpart identity the seller needs to fulfil the order."""

    customer_id: int


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class UnavailableItem(BaseModel):
    product_id: int
    product_name: str
    reason: str
    available_stock: int | None = None
