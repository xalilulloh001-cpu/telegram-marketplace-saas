"""Catalog data access.

Every function takes `shop_id` as a required argument and filters on it. There is no
code path here that can read or write another tenant's rows.
"""
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import UnaryExpression

from app.models.catalog import Category, Product, ProductImage
from app.repositories.base import Page

_SORTS: dict[str, UnaryExpression] = {
    "newest": Product.created_at.desc(),
    "oldest": Product.created_at.asc(),
    "price_asc": Product.price.asc(),
    "price_desc": Product.price.desc(),
    "name_asc": Product.name.asc(),
    "name_desc": Product.name.desc(),
}


async def _paginate(db: DbSession, stmt: Select, page: int, page_size: int) -> Page:
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    return Page(items=list(result.scalars().all()), page=page, page_size=page_size, total=total)


# --- categories -----------------------------------------------------------

async def get_category(db: DbSession, shop_id: int, category_id: int) -> Category | None:
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.shop_id == shop_id)
    )
    return result.scalar_one_or_none()


async def list_categories(db: DbSession, shop_id: int, page: int, page_size: int) -> Page:
    stmt = select(Category).where(Category.shop_id == shop_id).order_by(
        Category.sort_order.asc(), Category.name.asc()
    )
    return await _paginate(db, stmt, page, page_size)


async def category_slug_exists(
    db: DbSession, shop_id: int, slug: str, exclude_id: int | None = None
) -> bool:
    stmt = select(Category.id).where(Category.shop_id == shop_id, Category.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    return (await db.execute(stmt)).first() is not None


async def count_products_in_category(db: DbSession, shop_id: int, category_id: int) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.shop_id == shop_id, Product.category_id == category_id)
        )
        or 0
    )


async def count_child_categories(db: DbSession, shop_id: int, category_id: int) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(Category)
            .where(Category.shop_id == shop_id, Category.parent_id == category_id)
        )
        or 0
    )


# --- products -------------------------------------------------------------

async def get_product(db: DbSession, shop_id: int, product_id: int) -> Product | None:
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id, Product.shop_id == shop_id)
        .options(selectinload(Product.images))
    )
    return result.scalar_one_or_none()


async def list_products(
    db: DbSession,
    shop_id: int,
    page: int,
    page_size: int,
    search: str | None = None,
    category_id: int | None = None,
    is_active: bool | None = None,
    sort: str = "newest",
) -> Page:
    stmt = select(Product).where(Product.shop_id == shop_id)
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%"))
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if is_active is not None:
        stmt = stmt.where(Product.is_active.is_(is_active))
    # Sorting is looked up in a fixed map — a client string never reaches the SQL.
    stmt = stmt.order_by(_SORTS.get(sort, _SORTS["newest"]))
    return await _paginate(db, stmt, page, page_size)


async def product_slug_exists(
    db: DbSession, shop_id: int, slug: str, exclude_id: int | None = None
) -> bool:
    stmt = select(Product.id).where(Product.shop_id == shop_id, Product.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    return (await db.execute(stmt)).first() is not None


# --- product images -------------------------------------------------------

async def list_product_images(db: DbSession, shop_id: int, product_id: int) -> list[ProductImage]:
    result = await db.execute(
        select(ProductImage)
        .where(ProductImage.shop_id == shop_id, ProductImage.product_id == product_id)
        .order_by(ProductImage.sort_order.asc(), ProductImage.id.asc())
    )
    return list(result.scalars().all())


async def get_product_image(
    db: DbSession, shop_id: int, product_id: int, image_id: int
) -> ProductImage | None:
    result = await db.execute(
        select(ProductImage).where(
            ProductImage.id == image_id,
            ProductImage.product_id == product_id,
            ProductImage.shop_id == shop_id,
        )
    )
    return result.scalar_one_or_none()
