"""Seller category CRUD."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.deps import get_current_shop_id, require_permission
from app.core.rbac import Permission
from app.db.session import get_db
from app.models.catalog import Category
from app.models.tenancy import ShopMember
from app.repositories import catalog as repo
from app.repositories.base import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.catalog import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import PageResponse
from app.services import catalog_service

router = APIRouter(prefix="/seller/categories", tags=["seller-categories"])


@router.get("", response_model=PageResponse[CategoryResponse])
async def list_categories(
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_VIEW))],
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> PageResponse[CategoryResponse]:
    result = await repo.list_categories(db, shop_id, page, page_size)
    return PageResponse[CategoryResponse](
        items=[CategoryResponse.model_validate(c) for c in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        pages=result.pages,
    )


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.CATEGORY_WRITE))],
) -> Category:
    return await catalog_service.create_category(db, shop_id, payload)


@router.get("/{category_id}", response_model=CategoryResponse)
async def read_category(
    category_id: int,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_VIEW))],
) -> Category:
    return await catalog_service.get_category_or_404(db, shop_id, category_id)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.CATEGORY_WRITE))],
) -> Category:
    return await catalog_service.update_category(db, shop_id, category_id, payload)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.CATEGORY_WRITE))],
) -> None:
    await catalog_service.delete_category(db, shop_id, category_id)
