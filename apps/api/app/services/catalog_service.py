"""Catalog business rules.

Cross-tenant lookups return 404 rather than 403: a seller must not be able to learn that
another shop's category or product exists. This is applied consistently across the API.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.slugs import slugify
from app.models.catalog import Category, Product, ProductImage
from app.repositories import catalog as repo
from app.schemas.catalog import CategoryCreate, CategoryUpdate, ProductCreate, ProductUpdate

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


async def _unique_category_slug(db: DbSession, shop_id: int, name: str, exclude: int | None) -> str:
    base = slugify(name)
    slug = base
    suffix = 2
    while await repo.category_slug_exists(db, shop_id, slug, exclude):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


async def _unique_product_slug(db: DbSession, shop_id: int, name: str, exclude: int | None) -> str:
    base = slugify(name)
    slug = base
    suffix = 2
    while await repo.product_slug_exists(db, shop_id, slug, exclude):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


async def _resolve_parent(
    db: DbSession, shop_id: int, parent_id: int | None, self_id: int | None = None
) -> int | None:
    if parent_id is None:
        return None
    if self_id is not None and parent_id == self_id:
        raise _conflict("category cannot be its own parent")
    parent = await repo.get_category(db, shop_id, parent_id)
    if parent is None:
        # Another shop's category is indistinguishable from a non-existent one.
        raise _NOT_FOUND
    return parent.id


# --- categories -----------------------------------------------------------

async def create_category(db: DbSession, shop_id: int, payload: CategoryCreate) -> Category:
    parent_id = await _resolve_parent(db, shop_id, payload.parent_id)
    category = Category(
        shop_id=shop_id,
        name=payload.name,
        slug=await _unique_category_slug(db, shop_id, payload.name, None),
        parent_id=parent_id,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def get_category_or_404(db: DbSession, shop_id: int, category_id: int) -> Category:
    category = await repo.get_category(db, shop_id, category_id)
    if category is None:
        raise _NOT_FOUND
    return category


async def update_category(
    db: DbSession, shop_id: int, category_id: int, payload: CategoryUpdate
) -> Category:
    category = await get_category_or_404(db, shop_id, category_id)
    data = payload.model_dump(exclude_unset=True)

    if "parent_id" in data:
        category.parent_id = await _resolve_parent(db, shop_id, data["parent_id"], category.id)
    if "name" in data and data["name"] is not None:
        category.name = data["name"]
        category.slug = await _unique_category_slug(db, shop_id, data["name"], category.id)
    if data.get("is_active") is not None:
        category.is_active = data["is_active"]
    if data.get("sort_order") is not None:
        category.sort_order = data["sort_order"]

    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: DbSession, shop_id: int, category_id: int) -> None:
    """RESTRICT semantics: a category holding products or children cannot be removed,
    so no product is ever silently orphaned."""
    category = await get_category_or_404(db, shop_id, category_id)
    if await repo.count_products_in_category(db, shop_id, category.id):
        raise _conflict("category still has products")
    if await repo.count_child_categories(db, shop_id, category.id):
        raise _conflict("category still has subcategories")
    await db.delete(category)
    await db.commit()


# --- products -------------------------------------------------------------

async def _resolve_category(db: DbSession, shop_id: int, category_id: int | None) -> int | None:
    if category_id is None:
        return None
    category = await repo.get_category(db, shop_id, category_id)
    if category is None:
        raise _NOT_FOUND
    return category.id


async def create_product(db: DbSession, shop_id: int, payload: ProductCreate) -> Product:
    category_id = await _resolve_category(db, shop_id, payload.category_id)
    product = Product(
        shop_id=shop_id,  # from the tenant context, never from the request body
        category_id=category_id,
        name=payload.name,
        slug=await _unique_product_slug(db, shop_id, payload.name, None),
        description=payload.description,
        price=payload.price,
        discount_price=payload.discount_price,
        stock=payload.stock,
        is_active=payload.is_active,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def get_product_or_404(db: DbSession, shop_id: int, product_id: int) -> Product:
    product = await repo.get_product(db, shop_id, product_id)
    if product is None:
        raise _NOT_FOUND
    return product


async def update_product(
    db: DbSession, shop_id: int, product_id: int, payload: ProductUpdate
) -> Product:
    product = await get_product_or_404(db, shop_id, product_id)
    data = payload.model_dump(exclude_unset=True)

    if "category_id" in data:
        product.category_id = await _resolve_category(db, shop_id, data["category_id"])
    if "name" in data and data["name"] is not None:
        product.name = data["name"]
        product.slug = await _unique_product_slug(db, shop_id, data["name"], product.id)
    for field in ("description", "price", "discount_price", "stock", "is_active"):
        nullable_field = field in {"description", "discount_price"}
        if field in data and (data[field] is not None or nullable_field):
            setattr(product, field, data[field])

    price = product.price
    discount = product.discount_price
    if discount is not None and discount > price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="discount_price cannot exceed price",
        )

    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: DbSession, shop_id: int, product_id: int) -> None:
    product = await get_product_or_404(db, shop_id, product_id)
    await db.delete(product)
    await db.commit()


# --- images ---------------------------------------------------------------

async def add_product_image(
    db: DbSession, shop_id: int, product_id: int, url: str, sort_order: int = 0
) -> ProductImage:
    product = await get_product_or_404(db, shop_id, product_id)
    image = ProductImage(
        product_id=product.id, shop_id=shop_id, url=url, sort_order=sort_order
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def get_image_or_404(
    db: DbSession, shop_id: int, product_id: int, image_id: int
) -> ProductImage:
    image = await repo.get_product_image(db, shop_id, product_id, image_id)
    if image is None:
        raise _NOT_FOUND
    return image
