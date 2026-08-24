"""Customer cart and favorites. Scope always comes from the session, never the request."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.deps import get_current_customer
from app.db.session import get_db
from app.models.identity import Customer
from app.repositories import cart as repo
from app.repositories.base import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse, FavoriteResponse
from app.schemas.common import PageResponse
from app.services import cart_service
from app.services import customer_catalog_service as catalog_service

CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
Db = Annotated[DbSession, Depends(get_db)]

cart_router = APIRouter(prefix="/customer/shops/{shop_id}/cart", tags=["customer-cart"])
favorites_router = APIRouter(prefix="/customer/favorites", tags=["customer-favorites"])


@cart_router.get("", response_model=CartResponse)
async def read_cart(shop_id: int, customer: CurrentCustomer, db: Db) -> CartResponse:
    await catalog_service.get_shop_or_404(db, shop_id)
    return await cart_service.get_cart(db, customer.id, shop_id)


@cart_router.post("/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_item(
    shop_id: int, payload: CartItemAdd, customer: CurrentCustomer, db: Db
) -> CartResponse:
    await catalog_service.get_shop_or_404(db, shop_id)
    return await cart_service.add_item(
        db, customer.id, shop_id, payload.product_id, payload.quantity
    )


@cart_router.patch("/items/{item_id}", response_model=CartResponse)
async def update_item(
    shop_id: int, item_id: int, payload: CartItemUpdate, customer: CurrentCustomer, db: Db
) -> CartResponse:
    await catalog_service.get_shop_or_404(db, shop_id)
    return await cart_service.update_item(db, customer.id, shop_id, item_id, payload.quantity)


@cart_router.delete("/items/{item_id}", response_model=CartResponse)
async def remove_item(
    shop_id: int, item_id: int, customer: CurrentCustomer, db: Db
) -> CartResponse:
    await catalog_service.get_shop_or_404(db, shop_id)
    return await cart_service.remove_item(db, customer.id, shop_id, item_id)


@cart_router.delete("", response_model=CartResponse)
async def clear_cart(shop_id: int, customer: CurrentCustomer, db: Db) -> CartResponse:
    await catalog_service.get_shop_or_404(db, shop_id)
    return await cart_service.clear_cart(db, customer.id, shop_id)


@favorites_router.get("", response_model=PageResponse[FavoriteResponse])
async def list_favorites(
    customer: CurrentCustomer,
    db: Db,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> PageResponse[FavoriteResponse]:
    result = await repo.list_favorites(db, customer.id, page, page_size)
    return PageResponse[FavoriteResponse](
        items=[cart_service.to_favorite_response(f) for f in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        pages=result.pages,
    )


@favorites_router.put("/{product_id}", response_model=FavoriteResponse)
async def add_favorite(product_id: int, customer: CurrentCustomer, db: Db) -> FavoriteResponse:
    """PUT rather than POST: favouriting is idempotent, so repeating it is harmless."""
    return await cart_service.add_favorite(db, customer.id, product_id)


@favorites_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(product_id: int, customer: CurrentCustomer, db: Db) -> None:
    await cart_service.remove_favorite(db, customer.id, product_id)
