"""Reusable authentication and tenant-context dependencies.

Authorization lives here, never in route handlers. The rule that makes multi-tenancy safe:
`shop_id` is resolved from the server-side session and re-checked against `shop_members`.
A `shop_id` supplied by the client is only ever treated as a candidate.
"""
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.rbac import Permission, role_has_permission
from app.core.security import ADMIN_SESSION_COOKIE_NAME, SESSION_COOKIE_NAME
from app.db.session import get_db
from app.models.auth import Session
from app.models.enums import PrincipalType, ShopStatus
from app.models.identity import Customer, PlatformAdmin, User
from app.models.tenancy import Shop, ShopMember
from app.services import identity_service, session_service

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated"
)
_FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if header and header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


async def get_session(
    request: Request, db: Annotated[DbSession, Depends(get_db)]
) -> Session:
    """Customer Mini App sends a bearer token; browser panels send an httpOnly cookie."""
    token = (
        _bearer_token(request)
        or request.cookies.get(SESSION_COOKIE_NAME)
        or request.cookies.get(ADMIN_SESSION_COOKIE_NAME)
    )
    if not token:
        raise _UNAUTHENTICATED
    session = await session_service.resolve_session(db, token)
    if session is None:
        raise _UNAUTHENTICATED
    return session


async def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    db: Annotated[DbSession, Depends(get_db)],
) -> User:
    if session.user_id is None:
        raise _UNAUTHENTICATED
    user = await db.get(User, session.user_id)
    if user is None:
        raise _UNAUTHENTICATED
    return user


async def get_current_customer(
    session: Annotated[Session, Depends(get_session)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Customer:
    if session.principal_type is not PrincipalType.CUSTOMER or session.user_id is None:
        raise _FORBIDDEN
    result = await db.execute(select(Customer).where(Customer.user_id == session.user_id))
    customer = result.scalar_one_or_none()
    if customer is None:
        raise _UNAUTHENTICATED
    return customer


async def get_current_seller(
    session: Annotated[Session, Depends(get_session)],
    db: Annotated[DbSession, Depends(get_db)],
) -> ShopMember:
    """Re-reads the membership on every request, so revoking access takes effect at once."""
    if session.principal_type is not PrincipalType.SELLER:
        raise _FORBIDDEN
    if session.user_id is None or session.shop_id is None:
        raise _UNAUTHENTICATED
    membership = await identity_service.get_membership(db, session.user_id, session.shop_id)
    if membership is None:
        raise _FORBIDDEN
    return membership


async def get_current_shop(
    membership: Annotated[ShopMember, Depends(get_current_seller)],
    db: Annotated[DbSession, Depends(get_db)],
) -> Shop:
    shop = await db.get(Shop, membership.shop_id)
    if shop is None:
        raise _FORBIDDEN
    if shop.status is ShopStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="shop is blocked")
    return shop


async def get_current_shop_id(
    shop: Annotated[Shop, Depends(get_current_shop)],
) -> int:
    """The only sanctioned source of shop_id for seller-side queries."""
    return shop.id


def require_permission(permission: Permission) -> Callable[..., object]:
    async def dependency(
        membership: Annotated[ShopMember, Depends(get_current_seller)],
    ) -> ShopMember:
        if not role_has_permission(membership.role, permission):
            raise _FORBIDDEN
        return membership

    return dependency


async def get_current_platform_admin(
    session: Annotated[Session, Depends(get_session)],
    db: Annotated[DbSession, Depends(get_db)],
) -> PlatformAdmin:
    if session.principal_type is not PrincipalType.PLATFORM_ADMIN:
        raise _FORBIDDEN
    if session.platform_admin_id is None:
        raise _UNAUTHENTICATED
    admin = await db.get(PlatformAdmin, session.platform_admin_id)
    if admin is None or not admin.is_active:
        raise _FORBIDDEN
    return admin
