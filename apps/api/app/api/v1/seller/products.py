"""Seller product CRUD, listing with filters/sorting, and product images."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.deps import get_current_shop_id, require_permission
from app.core.rbac import Permission
from app.db.session import get_db
from app.models.catalog import Product, ProductImage
from app.models.tenancy import ShopMember
from app.repositories import catalog as repo
from app.repositories.base import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.catalog import (
    ProductCreate,
    ProductDetailResponse,
    ProductImageResponse,
    ProductImageUpdate,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.common import PageResponse
from app.services import catalog_service
from app.services.storage import UploadValidationError, get_object_storage
from app.services.storage.base import MAX_IMAGE_BYTES, build_key, validate_image

router = APIRouter(prefix="/seller/products", tags=["seller-products"])

# A closed set of sort keys — the client can only pick one of these, never write SQL.
SortOption = Literal["newest", "oldest", "price_asc", "price_desc", "name_asc", "name_desc"]


@router.get("", response_model=PageResponse[ProductResponse])
async def list_products(
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_VIEW))],
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    search: str | None = Query(None, max_length=128),
    category_id: int | None = None,
    is_active: bool | None = None,
    sort: SortOption = "newest",
) -> PageResponse[ProductResponse]:
    result = await repo.list_products(
        db,
        shop_id,
        page=page,
        page_size=page_size,
        search=search,
        category_id=category_id,
        is_active=is_active,
        sort=sort,
    )
    return PageResponse[ProductResponse](
        items=[ProductResponse.model_validate(p) for p in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        pages=result.pages,
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_WRITE))],
) -> Product:
    return await catalog_service.create_product(db, shop_id, payload)


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def read_product(
    product_id: int,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_VIEW))],
) -> Product:
    return await catalog_service.get_product_or_404(db, shop_id, product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_WRITE))],
) -> Product:
    return await catalog_service.update_product(db, shop_id, product_id, payload)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_WRITE))],
) -> None:
    await catalog_service.delete_product(db, shop_id, product_id)


# --- images ---------------------------------------------------------------

@router.get("/{product_id}/images", response_model=list[ProductImageResponse])
async def list_images(
    product_id: int,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_VIEW))],
) -> list[ProductImage]:
    await catalog_service.get_product_or_404(db, shop_id, product_id)
    return await repo.list_product_images(db, shop_id, product_id)


@router.post(
    "/{product_id}/images",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    product_id: int,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_WRITE))],
    file: UploadFile = File(...),
) -> ProductImage:
    """The URL is produced by our storage layer — a client-supplied URL is never stored."""
    product = await catalog_service.get_product_or_404(db, shop_id, product_id)
    data = await file.read(MAX_IMAGE_BYTES + 1)
    try:
        extension = validate_image(file.content_type, len(data))
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    key = build_key(shop_id, product.id, extension)
    stored = await get_object_storage().upload(key, data, str(file.content_type))
    return await catalog_service.add_product_image(db, shop_id, product.id, stored.url)


@router.patch("/{product_id}/images/{image_id}", response_model=ProductImageResponse)
async def update_image(
    product_id: int,
    image_id: int,
    payload: ProductImageUpdate,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_WRITE))],
) -> ProductImage:
    image = await catalog_service.get_image_or_404(db, shop_id, product_id, image_id)
    image.sort_order = payload.sort_order
    await db.commit()
    await db.refresh(image)
    return image


@router.delete("/{product_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    product_id: int,
    image_id: int,
    shop_id: Annotated[int, Depends(get_current_shop_id)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.PRODUCT_WRITE))],
) -> None:
    image = await catalog_service.get_image_or_404(db, shop_id, product_id, image_id)
    await db.delete(image)
    await db.commit()
