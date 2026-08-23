"""Resolves Telegram identities into global users/customers and shop memberships."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession
from sqlalchemy.orm import selectinload

from app.models.identity import Customer, User
from app.models.tenancy import Shop, ShopMember
from app.services.telegram_auth import TelegramUser


async def get_or_create_user(db: DbSession, tg_user: TelegramUser) -> User:
    result = await db.execute(select(User).where(User.telegram_id == tg_user.telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=tg_user.telegram_id)
        db.add(user)
    user.first_name = tg_user.first_name
    user.last_name = tg_user.last_name
    user.username = tg_user.username
    await db.commit()
    await db.refresh(user)
    return user


async def get_or_create_customer(db: DbSession, user: User) -> Customer:
    """Customers are global: one row per user, never per shop."""
    result = await db.execute(select(Customer).where(Customer.user_id == user.id))
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = Customer(user_id=user.id)
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
    return customer


async def list_shop_memberships(db: DbSession, user_id: int) -> list[ShopMember]:
    result = await db.execute(
        select(ShopMember)
        .where(ShopMember.user_id == user_id)
        .options(selectinload(ShopMember.shop))
    )
    return list(result.scalars().all())


async def get_membership(db: DbSession, user_id: int, shop_id: int) -> ShopMember | None:
    """The single source of truth for 'may this user act on this shop'."""
    result = await db.execute(
        select(ShopMember).where(ShopMember.user_id == user_id, ShopMember.shop_id == shop_id)
    )
    return result.scalar_one_or_none()


async def get_shop(db: DbSession, shop_id: int) -> Shop | None:
    result = await db.execute(select(Shop).where(Shop.id == shop_id))
    return result.scalar_one_or_none()
