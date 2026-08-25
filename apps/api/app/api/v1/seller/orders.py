"""Seller order board."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.deps import get_current_shop_id, require_permission
from app.core.rbac import Permission
from app.db.session import get_db
from app.models.enums import OrderStatus
from app.models.tenancy import ShopMember
from app.repositories import orders as repo
from app.repositories.base import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.common import PageResponse
from app.schemas.orders import OrderResponse, OrderStatusUpdate, SellerOrderResponse
from app.services import order_service

router = APIRouter(prefix="/seller/orders", tags=["seller-orders"])

Db = Annotated[DbSession, Depends(get_db)]
ShopId = Annotated[int, Depends(get_current_shop_id)]


@router.get("", response_model=PageResponse[OrderResponse])
async def list_orders(
    shop_id: ShopId,
    db: Db,
    _: Annotated[ShopMember, Depends(require_permission(Permission.ORDER_VIEW))],
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    order_status: OrderStatus | None = Query(None, alias="status"),
) -> PageResponse[OrderResponse]:
    result = await repo.list_shop_orders(db, shop_id, page, page_size, status=order_status)
    return PageResponse[OrderResponse](
        items=[order_service.to_order_response(o) for o in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        pages=result.pages,
    )


@router.get("/{order_id}", response_model=SellerOrderResponse)
async def read_order(
    order_id: int,
    shop_id: ShopId,
    db: Db,
    _: Annotated[ShopMember, Depends(require_permission(Permission.ORDER_VIEW))],
) -> SellerOrderResponse:
    order = await order_service.get_shop_order_or_404(db, shop_id, order_id)
    return order_service.to_seller_order(order)


@router.patch("/{order_id}/status", response_model=SellerOrderResponse)
async def update_status(
    order_id: int,
    payload: OrderStatusUpdate,
    shop_id: ShopId,
    db: Db,
    _: Annotated[ShopMember, Depends(require_permission(Permission.ORDER_UPDATE))],
) -> SellerOrderResponse:
    order = await order_service.get_shop_order_or_404(db, shop_id, order_id)
    await order_service.change_status(db, order, payload.status)
    refreshed = await order_service.get_shop_order_or_404(db, shop_id, order_id)
    return order_service.to_seller_order(refreshed)
