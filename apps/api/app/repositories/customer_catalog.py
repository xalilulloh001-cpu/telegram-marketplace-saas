"""Read-only catalog queries for customers.

Two invariants hold in every function here:
  1. results are constrained to one shop (`shop_id` is a required argument), and
  2. only publicly visible rows are returned — inactive products/categories and
     non-active shops are filtered out at the query level, not in the response layer.
"""
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import UnaryExpression

from app.models.catalog import Category, Product
from app.models.enums import ShopStatus
from app.models.tenancy import Shop
from app.repositories.base import Page

# A shop is only discoverable once it is fully active; trial and blocked shops stay hidden.
PUBLIC_SHOP_STATUSES = (ShopStatus.ACTIVE,)

_PRODUCT_SORTS: dict[str, UnaryExpression] = {
    "newest": Product.created_at.desc(),
    "price_asc": Product.price.asc(),
    "price_desc": Product.price.desc(),
    "name_asc": Product.name.asc(),
    "name_desc": Product.name.desc(),
}

_SHOP_SORTS: dict[str, UnaryExpression] = {
    "newest": Shop.created_at.desc(),
    "name_asc": Shop.name.asc(),
    "name_desc": Shop.name.desc(),
}


async def _paginate(db: DbSession, stmt: Select, page: int, page_size: int) -> Page:
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    return Page(items=list(result.scalars().all()), page=page, page_size=page_size, total=total)


# --- shops ----------------------------------------------------------------

async def list_public_shops(
    db: DbSession, page: int, page_size: int, search: str | None = None, sort: str = "newest"
) -> Page:
    stmt = select(Shop).where(Shop.status.in_(PUBLIC_SHOP_STATUSES))
    if search:
        stmt = stmt.where(Shop.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(_SHOP_SORTS.get(sort, _SHOP_SORTS["newest"]))
    return await _paginate(db, stmt, page, page_size)


async def get_public_shop(db: DbSession, shop_id: int) -> Shop | None:
    result = await db.execute(
        select(Shop).where(Shop.id == shop_id, Shop.status.in_(PUBLIC_SHOP_STATUSES))
    )
    return result.scalar_one_or_none()


# --- categories -----------------------------------------------------------

async def list_public_categories(db: DbSession, shop_id: int) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(Category.shop_id == shop_id, Category.is_active.is_(True))
        .order_by(Category.sort_order.asc(), Category.name.asc())
    )
    return list(result.scalars().all())


async def get_public_category(db: DbSession, shop_id: int, category_id: int) -> Category | None:
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.shop_id == shop_id,
            Category.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


# --- products -------------------------------------------------------------

def _public_products(shop_id: int) -> Select:
    return select(Product).where(Product.shop_id == shop_id, Product.is_active.is_(True))


async def list_public_products(
    db: DbSession,
    shop_id: int,
    page: int,
    page_size: int,
    search: str | None = None,
    category_id: int | None = None,
    in_stock: bool | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    sort: str = "newest",
) -> Page:
    stmt = _public_products(shop_id)
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%"))
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if in_stock is True:
        stmt = stmt.where(Product.stock > 0)
    elif in_stock is False:
        stmt = stmt.where(Product.stock <= 0)
    if price_min is not None:
        stmt = stmt.where(Product.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(Product.price <= price_max)
    # Images are eager-loaded so rendering a page of cards stays a fixed number of queries.
    stmt = stmt.options(selectinload(Product.images))
    stmt = stmt.order_by(_PRODUCT_SORTS.get(sort, _PRODUCT_SORTS["newest"]))
    return await _paginate(db, stmt, page, page_size)


async def get_public_product(db: DbSession, shop_id: int, product_id: int) -> Product | None:
    result = await db.execute(
        _public_products(shop_id)
        .where(Product.id == product_id)
        .options(selectinload(Product.images), selectinload(Product.category))
    )
    return result.scalar_one_or_none()
