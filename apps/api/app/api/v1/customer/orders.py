"""Customer checkout and order history."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.deps import get_current_customer
from app.db.session import get_db
from app.models.enums import OrderStatus
from app.models.identity import Customer
from app.repositories import orders as repo
from app.repositories.base import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.common import PageResponse
from app.schemas.orders import CheckoutRequest, OrderDetailResponse, OrderResponse
from app.services import customer_catalog_service as catalog_service
from app.services import order_service

CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
Db = Annotated[DbSession, Depends(get_db)]

checkout_router = APIRouter(prefix="/customer/shops/{shop_id}", tags=["customer-checkout"])
orders_router = APIRouter(prefix="/customer/orders", tags=["customer-orders"])


@checkout_router.post(
    "/checkout", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED
)
async def checkout(
    shop_id: int, payload: CheckoutRequest, customer: CurrentCustomer, db: Db
) -> OrderDetailResponse:
    """One checkout creates exactly one order for one shop."""
    await catalog_service.get_shop_or_404(db, shop_id)
    return await order_service.checkout(db, customer, shop_id, payload)


@orders_router.get("", response_model=PageResponse[OrderResponse])
async def list_orders(
    customer: CurrentCustomer,
    db: Db,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> PageResponse[OrderResponse]:
    result = await repo.list_customer_orders(db, customer.id, page, page_size)
    return PageResponse[OrderResponse](
        items=[order_service.to_order_response(o) for o in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        pages=result.pages,
    )


@orders_router.get("/{order_id}", response_model=OrderDetailResponse)
async def read_order(order_id: int, customer: CurrentCustomer, db: Db) -> OrderDetailResponse:
    order = await order_service.get_customer_order_or_404(db, customer.id, order_id)
    return order_service.to_order_detail(order)


@orders_router.post("/{order_id}/cancel", response_model=OrderDetailResponse)
async def cancel_order(
    order_id: int, customer: CurrentCustomer, db: Db
) -> OrderDetailResponse:
    """Customers may cancel only while the order is still PENDING — once the seller has
    confirmed it, cancellation becomes a seller decision."""
    order = await order_service.get_customer_order_or_404(db, customer.id, order_id)
    if order.status is not OrderStatus.PENDING:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="only pending orders can be cancelled by the customer",
        )
    updated = await order_service.change_status(db, order, OrderStatus.CANCELLED)
    refreshed = await order_service.get_customer_order_or_404(db, customer.id, updated.id)
    return order_service.to_order_detail(refreshed)
