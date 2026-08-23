"""Seller shop settings and members. shop_id always comes from the tenant context."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.deps import get_current_seller, get_current_shop, require_permission
from app.core.rbac import Permission
from app.db.session import get_db
from app.models.tenancy import Shop, ShopMember
from app.schemas.tenancy import (
    MemberCreate,
    MemberResponse,
    MemberUpdate,
    ShopResponse,
    ShopUpdate,
)
from app.services import shop_service

router = APIRouter(prefix="/seller/shop", tags=["seller-shop"])


@router.get("", response_model=ShopResponse)
async def read_shop(shop: Annotated[Shop, Depends(get_current_shop)]) -> Shop:
    return shop


@router.patch("", response_model=ShopResponse)
async def update_shop(
    payload: ShopUpdate,
    shop: Annotated[Shop, Depends(get_current_shop)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.SHOP_SETTINGS_WRITE))],
) -> Shop:
    return await shop_service.update_shop(db, shop, payload)


@router.get("/members", response_model=list[MemberResponse])
async def list_members(
    shop: Annotated[Shop, Depends(get_current_shop)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.MEMBER_VIEW))],
) -> list[MemberResponse]:
    return await shop_service.list_members(db, shop.id)


@router.post("/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    payload: MemberCreate,
    shop: Annotated[Shop, Depends(get_current_shop)],
    db: Annotated[DbSession, Depends(get_db)],
    _: Annotated[ShopMember, Depends(require_permission(Permission.MEMBER_MANAGE))],
) -> MemberResponse:
    return await shop_service.add_member(db, shop.id, payload)


@router.patch("/members/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: int,
    payload: MemberUpdate,
    shop: Annotated[Shop, Depends(get_current_shop)],
    db: Annotated[DbSession, Depends(get_db)],
    actor: Annotated[ShopMember, Depends(require_permission(Permission.MEMBER_MANAGE))],
) -> MemberResponse:
    return await shop_service.update_member_role(db, shop.id, member_id, actor, payload)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: int,
    shop: Annotated[Shop, Depends(get_current_shop)],
    db: Annotated[DbSession, Depends(get_db)],
    actor: Annotated[ShopMember, Depends(require_permission(Permission.MEMBER_MANAGE))],
) -> None:
    await shop_service.remove_member(db, shop.id, member_id, actor)


__all__ = ["router", "get_current_seller"]
