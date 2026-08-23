"""Shop and membership data access — always scoped to a single shop."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession
from sqlalchemy.orm import selectinload

from app.models.enums import ShopMemberRole
from app.models.identity import User
from app.models.tenancy import ShopMember


async def list_members(db: DbSession, shop_id: int) -> list[ShopMember]:
    result = await db.execute(
        select(ShopMember)
        .where(ShopMember.shop_id == shop_id)
        .options(selectinload(ShopMember.user))
        .order_by(ShopMember.id.asc())
    )
    return list(result.scalars().all())


async def get_member(db: DbSession, shop_id: int, member_id: int) -> ShopMember | None:
    result = await db.execute(
        select(ShopMember)
        .where(ShopMember.id == member_id, ShopMember.shop_id == shop_id)
        .options(selectinload(ShopMember.user))
    )
    return result.scalar_one_or_none()


async def get_member_by_telegram_id(
    db: DbSession, shop_id: int, telegram_id: int
) -> ShopMember | None:
    result = await db.execute(
        select(ShopMember)
        .join(User, User.id == ShopMember.user_id)
        .where(ShopMember.shop_id == shop_id, User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def count_owners(db: DbSession, shop_id: int) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(ShopMember)
            .where(ShopMember.shop_id == shop_id, ShopMember.role == ShopMemberRole.OWNER)
        )
        or 0
    )
