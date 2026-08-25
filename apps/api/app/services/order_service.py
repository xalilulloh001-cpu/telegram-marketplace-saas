"""Checkout and order lifecycle.

Checkout is **shop-scoped**: one checkout creates exactly one order for exactly one shop.
A customer with items in three shops checks out three times. Multi-shop checkout is
deliberately out of scope for the MVP — the schema supports adding it later.

The whole of checkout runs in one transaction. Products are locked in a deterministic
order, stock and prices are read from the database (never from the request), and if any
line fails the entire operation rolls back — no partial orders.
"""
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.models.catalog import Product
from app.models.enums import OrderStatus
from app.models.identity import Address, Customer, User
from app.models.orders import Order, OrderItem
from app.repositories import cart as cart_repo
from app.repositories import orders as repo
from app.schemas.orders import (
    CheckoutRequest,
    OrderDetailResponse,
    OrderItemResponse,
    OrderResponse,
    SellerOrderResponse,
)

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

# Forward transitions plus the points at which an order may still be cancelled.
ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.PROCESSING, OrderStatus.CANCELLED}),
    OrderStatus.PROCESSING: frozenset({OrderStatus.SHIPPED, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

# Cancelling from these states must return the reserved stock to the shelf.
STOCK_HOLDING_STATUSES = frozenset(
    {OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.SHIPPED}
)


def _conflict(detail: str, extra: object | None = None) -> HTTPException:
    payload: object = detail if extra is None else {"message": detail, "items": extra}
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=payload)


def _unit_price(product: Product) -> Decimal:
    return product.discount_price if product.discount_price is not None else product.price


# --- responses ------------------------------------------------------------

def _item_response(item: OrderItem) -> OrderItemResponse:
    return OrderItemResponse(
        id=item.id,
        product_id=item.product_id,
        product_name=item.product_name_snapshot,
        list_price=item.list_price_snapshot,
        unit_price=item.price_snapshot,
        quantity=item.qty,
        line_total=item.price_snapshot * item.qty,
    )


def to_order_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        shop_id=order.shop_id,
        shop_name=order.shop.name if order.shop else None,
        status=order.status,
        subtotal=order.subtotal,
        total=order.total_amount,
        total_items=sum(i.qty for i in order.items),
        created_at=order.created_at,
    )


def to_order_detail(order: Order) -> OrderDetailResponse:
    base = to_order_response(order)
    return OrderDetailResponse(
        **base.model_dump(),
        items=[_item_response(i) for i in sorted(order.items, key=lambda i: i.id)],
        address_snapshot=order.address_snapshot,
        phone_snapshot=order.phone_snapshot,
        customer_name_snapshot=order.customer_name_snapshot,
        comment=order.comment,
        updated_at=order.updated_at,
    )


def to_seller_order(order: Order) -> SellerOrderResponse:
    detail = to_order_detail(order)
    return SellerOrderResponse(**detail.model_dump(), customer_id=order.customer_id)


# --- checkout -------------------------------------------------------------

async def _next_order_number(db: DbSession, shop_id: int) -> str:
    """Draws the next per-shop number under a row lock, so concurrent checkouts in the
    same shop cannot produce a duplicate."""
    shop = await repo.lock_shop_for_numbering(db, shop_id)
    if shop is None:  # pragma: no cover - shop existence is checked by the caller
        raise _NOT_FOUND
    shop.order_seq += 1
    return f"{shop.order_prefix}-{shop.order_seq}"


async def _resolve_address(
    db: DbSession, customer: Customer, address_id: int | None
) -> Address | None:
    if address_id is None:
        return None
    result = await db.execute(
        select(Address).where(Address.id == address_id, Address.customer_id == customer.id)
    )
    address = result.scalar_one_or_none()
    if address is None:
        # Another customer's address is reported as simply not existing.
        raise _NOT_FOUND
    return address


async def checkout(
    db: DbSession, customer: Customer, shop_id: int, payload: CheckoutRequest
) -> OrderDetailResponse:
    if payload.idempotency_key:
        existing = await repo.find_by_idempotency_key(db, customer.id, payload.idempotency_key)
        if existing is not None:
            # A double-tapped confirm button returns the order that was already created.
            return to_order_detail(existing)

    cart = await cart_repo.get_cart(db, customer.id, shop_id)
    if cart is None or not cart.items:
        raise _conflict("cart is empty")

    address = await _resolve_address(db, customer, payload.address_id)

    # Deterministic lock order (product_id ascending) keeps concurrent checkouts from
    # deadlocking against each other.
    items = sorted(cart.items, key=lambda i: i.product_id)

    unavailable: list[dict[str, object]] = []
    lines: list[tuple[Product, int, Decimal]] = []

    for item in items:
        product = await cart_repo.lock_product(db, shop_id, item.product_id)
        if product is None or not product.is_active:
            unavailable.append(
                {
                    "product_id": item.product_id,
                    "product_name": item.product.name if item.product else "",
                    "reason": "unavailable",
                    "available_stock": None,
                }
            )
            continue
        if product.stock < item.qty:
            unavailable.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "reason": "insufficient_stock",
                    "available_stock": product.stock,
                }
            )
            continue
        lines.append((product, item.qty, _unit_price(product)))

    if unavailable:
        # Nothing has been written yet, so the rollback is implicit: the cart is untouched
        # and the customer is told exactly which lines blocked the order.
        await db.rollback()
        raise _conflict("some items are no longer available", unavailable)

    customer_name = await _customer_name(db, customer)
    order_number = await _next_order_number(db, shop_id)
    subtotal = sum((price * qty for _, qty, price in lines), Decimal("0"))

    order = Order(
        shop_id=shop_id,
        customer_id=customer.id,
        order_number=order_number,
        status=OrderStatus.PENDING,
        subtotal=subtotal,
        total_amount=subtotal,  # no shipping/tax in the MVP
        address_id=address.id if address else None,
        address_snapshot=address.full_address if address else None,
        phone_snapshot=payload.phone or (address.phone if address else None),
        customer_name_snapshot=customer_name,
        comment=payload.comment,
        idempotency_key=payload.idempotency_key,
    )
    db.add(order)
    await db.flush()

    for product, qty, price in lines:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name_snapshot=product.name,
                list_price_snapshot=product.price,
                price_snapshot=price,
                qty=qty,
            )
        )
        product.stock -= qty

    cart.items.clear()

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if payload.idempotency_key:
            existing = await repo.find_by_idempotency_key(db, customer.id, payload.idempotency_key)
            if existing is not None:
                return to_order_detail(existing)
        raise _conflict("checkout could not be completed") from exc

    created = await repo.get_customer_order(db, customer.id, order.id)
    if created is None:  # pragma: no cover - defensive
        raise _NOT_FOUND
    return to_order_detail(created)


async def _customer_name(db: DbSession, customer: Customer) -> str | None:
    """Loaded explicitly — lazy relationship access is not available in an async session."""
    user = await db.get(User, customer.user_id)
    if user is None:  # pragma: no cover - defensive
        return None
    parts = [p for p in (user.first_name, user.last_name) if p]
    return " ".join(parts) or user.username


# --- lifecycle ------------------------------------------------------------

async def _restore_stock(db: DbSession, order: Order) -> None:
    for item in order.items:
        if item.product_id is None:
            continue
        product = await cart_repo.lock_product(db, order.shop_id, item.product_id)
        if product is not None:
            product.stock += item.qty


async def change_status(
    db: DbSession, order: Order, new_status: OrderStatus
) -> Order:
    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise _conflict(f"cannot move order from {order.status.value} to {new_status.value}")

    if new_status is OrderStatus.CANCELLED and order.status in STOCK_HOLDING_STATUSES:
        await _restore_stock(db, order)

    order.status = new_status
    await db.commit()
    await db.refresh(order)
    return order


async def get_customer_order_or_404(db: DbSession, customer_id: int, order_id: int) -> Order:
    order = await repo.get_customer_order(db, customer_id, order_id)
    if order is None:
        raise _NOT_FOUND
    return order


async def get_shop_order_or_404(db: DbSession, shop_id: int, order_id: int) -> Order:
    order = await repo.get_shop_order(db, shop_id, order_id)
    if order is None:
        raise _NOT_FOUND
    return order
