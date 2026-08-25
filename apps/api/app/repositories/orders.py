"""Order data access. Every query is scoped by customer_id or shop_id."""
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession
from sqlalchemy.orm import selectinload

from app.models.enums import OrderStatus
from app.models.orders import Order
from app.models.tenancy import Shop
from app.repositories.base import Page

_DETAIL_OPTIONS = (selectinload(Order.items), selectinload(Order.shop))


async def _paginate(db: DbSession, stmt: Select, page: int, page_size: int) -> Page:
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    return Page(items=list(result.scalars().all()), page=page, page_size=page_size, total=total)


async def list_customer_orders(db: DbSession, customer_id: int, page: int, page_size: int) -> Page:
    stmt = (
        select(Order)
        .where(Order.customer_id == customer_id)
        .options(*_DETAIL_OPTIONS)
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    return await _paginate(db, stmt, page, page_size)


async def get_customer_order(db: DbSession, customer_id: int, order_id: int) -> Order | None:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.customer_id == customer_id)
        .options(*_DETAIL_OPTIONS)
    )
    return result.scalar_one_or_none()


async def list_shop_orders(
    db: DbSession, shop_id: int, page: int, page_size: int, status: OrderStatus | None = None
) -> Page:
    stmt = select(Order).where(Order.shop_id == shop_id)
    if status is not None:
        stmt = stmt.where(Order.status == status)
    stmt = stmt.options(*_DETAIL_OPTIONS).order_by(Order.created_at.desc(), Order.id.desc())
    return await _paginate(db, stmt, page, page_size)


async def get_shop_order(db: DbSession, shop_id: int, order_id: int) -> Order | None:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.shop_id == shop_id)
        .options(*_DETAIL_OPTIONS)
    )
    return result.scalar_one_or_none()


async def find_by_idempotency_key(db: DbSession, customer_id: int, key: str) -> Order | None:
    result = await db.execute(
        select(Order)
        .where(Order.customer_id == customer_id, Order.idempotency_key == key)
        .options(*_DETAIL_OPTIONS)
    )
    return result.scalar_one_or_none()


async def lock_shop_for_numbering(db: DbSession, shop_id: int) -> Shop | None:
    """Locks the shop row so two concurrent checkouts cannot draw the same order number."""
    result = await db.execute(select(Shop).where(Shop.id == shop_id).with_for_update())
    return result.scalar_one_or_none()
