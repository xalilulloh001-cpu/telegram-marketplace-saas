"""Read-only customer catalog: shop discovery, categories, products."""
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.deps import get_current_customer
from app.db.session import get_db
from app.models.identity import Customer
from app.repositories import customer_catalog as repo
from app.repositories.base import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.common import PageResponse
from app.schemas.customer import (
    CustomerCategoryResponse,
    CustomerProductDetailResponse,
    CustomerProductResponse,
    CustomerShopDetailResponse,
    CustomerShopResponse,
)
from app.services import customer_catalog_service as service

router = APIRouter(prefix="/customer/shops", tags=["customer-catalog"])

# Closed sets — an unknown value is rejected by FastAPI before reaching the query.
ProductSort = Literal["newest", "price_asc", "price_desc", "name_asc", "name_desc"]
ShopSort = Literal["newest", "name_asc", "name_desc"]

CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
Db = Annotated[DbSession, Depends(get_db)]


@router.get("", response_model=PageResponse[CustomerShopResponse])
async def list_shops(
    _: CurrentCustomer,
    db: Db,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    search: str | None = Query(None, max_length=128),
    sort: ShopSort = "newest",
) -> PageResponse[CustomerShopResponse]:
    result = await repo.list_public_shops(db, page, page_size, search=search, sort=sort)
    return PageResponse[CustomerShopResponse](
        items=[CustomerShopResponse.model_validate(s) for s in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        pages=result.pages,
    )


@router.get("/{shop_id}", response_model=CustomerShopDetailResponse)
async def read_shop(shop_id: int, _: CurrentCustomer, db: Db) -> CustomerShopDetailResponse:
    shop = await service.get_shop_or_404(db, shop_id)
    return CustomerShopDetailResponse.model_validate(shop)


@router.get("/{shop_id}/categories", response_model=list[CustomerCategoryResponse])
async def list_categories(
    shop_id: int, _: CurrentCustomer, db: Db
) -> list[CustomerCategoryResponse]:
    await service.get_shop_or_404(db, shop_id)
    categories = await repo.list_public_categories(db, shop_id)
    return [CustomerCategoryResponse.model_validate(c) for c in categories]


@router.get("/{shop_id}/products", response_model=PageResponse[CustomerProductResponse])
async def list_products(
    shop_id: int,
    _: CurrentCustomer,
    db: Db,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    search: str | None = Query(None, max_length=128),
    category_id: int | None = None,
    in_stock: bool | None = None,
    price_min: Decimal | None = Query(None, ge=0),
    price_max: Decimal | None = Query(None, ge=0),
    sort: ProductSort = "newest",
) -> PageResponse[CustomerProductResponse]:
    await service.get_shop_or_404(db, shop_id)

    if price_min is not None and price_max is not None and price_min > price_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="price_min cannot exceed price_max",
        )
    if category_id is not None:
        # Resolving here means another shop's category id yields 404, not an empty list.
        await service.resolve_category_or_404(db, shop_id, category_id)

    result = await repo.list_public_products(
        db,
        shop_id,
        page=page,
        page_size=page_size,
        search=search,
        category_id=category_id,
        in_stock=in_stock,
        price_min=price_min,
        price_max=price_max,
        sort=sort,
    )
    return PageResponse[CustomerProductResponse](
        items=[service.to_product_response(p) for p in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        pages=result.pages,
    )


@router.get("/{shop_id}/products/{product_id}", response_model=CustomerProductDetailResponse)
async def read_product(
    shop_id: int, product_id: int, _: CurrentCustomer, db: Db
) -> CustomerProductDetailResponse:
    await service.get_shop_or_404(db, shop_id)
    return await service.get_product_detail_or_404(db, shop_id, product_id)
