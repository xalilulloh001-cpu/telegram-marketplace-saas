"""Shop settings and membership rules."""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.models.enums import ShopMemberRole
from app.models.identity import User
from app.models.tenancy import Shop, ShopMember
from app.repositories import tenancy as repo
from app.schemas.tenancy import MemberCreate, MemberResponse, MemberUpdate, ShopUpdate

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")


async def update_shop(db: DbSession, shop: Shop, payload: ShopUpdate) -> Shop:
    """Only the whitelisted fields on ShopUpdate can move — slug, status and plan_id
    are not exposed, so a crafted body cannot escalate a shop's state."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(shop, field, str(value) if field == "contact_email" and value else value)
    await db.commit()
    await db.refresh(shop)
    return shop


def to_member_response(member: ShopMember) -> MemberResponse:
    return MemberResponse(
        id=member.id,
        user_id=member.user_id,
        telegram_id=member.user.telegram_id,
        username=member.user.username,
        first_name=member.user.first_name,
        role=member.role,
        created_at=member.created_at,
    )


async def list_members(db: DbSession, shop_id: int) -> list[MemberResponse]:
    return [to_member_response(m) for m in await repo.list_members(db, shop_id)]


async def add_member(db: DbSession, shop_id: int, payload: MemberCreate) -> MemberResponse:
    if await repo.get_member_by_telegram_id(db, shop_id, payload.telegram_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already a member")

    result = await db.execute(select(User).where(User.telegram_id == payload.telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        # The invitee is created as an identity now and claims it on first Telegram login.
        user = User(telegram_id=payload.telegram_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    member = ShopMember(shop_id=shop_id, user_id=user.id, role=payload.role)
    db.add(member)
    await db.commit()
    created = await repo.get_member(db, shop_id, member.id)
    if created is None:  # pragma: no cover - defensive
        raise _NOT_FOUND
    return to_member_response(created)


async def update_member_role(
    db: DbSession, shop_id: int, member_id: int, actor: ShopMember, payload: MemberUpdate
) -> MemberResponse:
    member = await repo.get_member(db, shop_id, member_id)
    if member is None:
        raise _NOT_FOUND
    if member.id == actor.id and payload.role is not ShopMemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="cannot change your own role"
        )
    if member.role is ShopMemberRole.OWNER and payload.role is not ShopMemberRole.OWNER:
        if await repo.count_owners(db, shop_id) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="shop must keep one owner"
            )
    member.role = payload.role
    await db.commit()
    await db.refresh(member)
    return to_member_response(member)


async def remove_member(db: DbSession, shop_id: int, member_id: int, actor: ShopMember) -> None:
    member = await repo.get_member(db, shop_id, member_id)
    if member is None:
        raise _NOT_FOUND
    if member.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="cannot remove yourself"
        )
    if member.role is ShopMemberRole.OWNER and await repo.count_owners(db, shop_id) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="shop must keep one owner"
        )
    await db.delete(member)
    await db.commit()
