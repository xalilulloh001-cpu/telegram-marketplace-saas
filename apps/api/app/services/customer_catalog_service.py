"""Assembles customer-facing catalog responses."""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.models.catalog import Category, Product
from app.models.tenancy import Shop
from app.repositories import customer_catalog as repo
from app.schemas.customer import (
    CustomerCategoryResponse,
    CustomerProductDetailResponse,
    CustomerProductImageResponse,
    CustomerProductResponse,
)

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")


async def get_shop_or_404(db: DbSession, shop_id: int) -> Shop:
    """A hidden shop is reported exactly like a non-existent one."""
    shop = await repo.get_public_shop(db, shop_id)
    if shop is None:
        raise _NOT_FOUND
    return shop


async def resolve_category_or_404(db: DbSession, shop_id: int, category_id: int) -> Category:
    category = await repo.get_public_category(db, shop_id, category_id)
    if category is None:
        raise _NOT_FOUND
    return category


def to_product_response(product: Product) -> CustomerProductResponse:
    images = sorted(product.images, key=lambda i: (i.sort_order, i.id))
    return CustomerProductResponse(
        id=product.id,
        name=product.name,
        slug=product.slug,
        price=product.price,
        discount_price=product.discount_price,
        category_id=product.category_id,
        image_url=images[0].url if images else None,
        # Availability is exposed as a boolean — the exact stock count stays internal.
        in_stock=product.stock > 0,
    )


def to_product_detail(product: Product) -> CustomerProductDetailResponse:
    images = sorted(product.images, key=lambda i: (i.sort_order, i.id))
    category = product.category
    return CustomerProductDetailResponse(
        id=product.id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        price=product.price,
        discount_price=product.discount_price,
        category_id=product.category_id,
        image_url=images[0].url if images else None,
        in_stock=product.stock > 0,
        images=[CustomerProductImageResponse(id=i.id, url=i.url) for i in images],
        category=(
            CustomerCategoryResponse(
                id=category.id,
                name=category.name,
                slug=category.slug,
                parent_id=category.parent_id,
            )
            if category is not None and category.is_active
            else None
        ),
        created_at=product.created_at,
    )


async def get_product_detail_or_404(
    db: DbSession, shop_id: int, product_id: int
) -> CustomerProductDetailResponse:
    product = await repo.get_public_product(db, shop_id, product_id)
    if product is None:
        raise _NOT_FOUND
    return to_product_detail(product)
