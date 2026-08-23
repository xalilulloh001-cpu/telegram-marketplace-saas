"""Telegram-backed authentication for customers and sellers."""
import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.config import get_settings
from app.core.deps import get_session
from app.core.rbac import ROLE_PERMISSIONS
from app.core.security import SESSION_COOKIE_NAME
from app.db.session import get_db
from app.models.auth import Session
from app.models.enums import PrincipalType
from app.models.identity import User
from app.schemas.auth import (
    CurrentUserResponse,
    CustomerAuthResponse,
    SellerAuthResponse,
    ShopSummary,
    TelegramAuthRequest,
)
from app.services import identity_service, session_service
from app.services.telegram_auth import TelegramAuthError, verify_init_data

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

_INVALID = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid telegram login")


async def _verify(init_data: str, db: DbSession):
    try:
        verified = verify_init_data(
            init_data,
            settings.telegram_bot_token or "",
            settings.telegram_auth_max_age_seconds,
        )
    except TelegramAuthError as exc:
        raise _INVALID from exc

    fingerprint = hashlib.sha256(init_data.encode()).hexdigest()
    fresh = await session_service.consume_telegram_nonce(
        db, fingerprint, settings.telegram_auth_max_age_seconds
    )
    if not fresh:
        raise _INVALID
    return verified


@router.post("/telegram", response_model=CustomerAuthResponse)
async def telegram_customer_login(
    payload: TelegramAuthRequest,
    request: Request,
    db: Annotated[DbSession, Depends(get_db)],
) -> CustomerAuthResponse:
    verified = await _verify(payload.init_data, db)
    user = await identity_service.get_or_create_user(db, verified.user)
    customer = await identity_service.get_or_create_customer(db, user)
    token = await session_service.create_session(
        db,
        principal_type=PrincipalType.CUSTOMER,
        ttl_seconds=settings.session_ttl_seconds,
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
    )
    return CustomerAuthResponse(
        access_token=token, telegram_id=user.telegram_id, customer_id=customer.id
    )


@router.post("/telegram/seller", response_model=SellerAuthResponse)
async def telegram_seller_login(
    payload: TelegramAuthRequest,
    request: Request,
    response: Response,
    db: Annotated[DbSession, Depends(get_db)],
) -> SellerAuthResponse:
    """The client may name a shop, but membership decides — an unmatched shop_id is refused."""
    verified = await _verify(payload.init_data, db)
    user = await identity_service.get_or_create_user(db, verified.user)
    memberships = await identity_service.list_shop_memberships(db, user.id)
    available = [
        ShopSummary(id=m.shop.id, name=m.shop.name, slug=m.shop.slug, role=m.role)
        for m in memberships
    ]
    if not available:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="no shop membership")

    if payload.shop_id is not None:
        selected = next((m for m in memberships if m.shop_id == payload.shop_id), None)
        if selected is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    else:
        selected = memberships[0] if len(memberships) == 1 else None

    token = await session_service.create_session(
        db,
        principal_type=PrincipalType.SELLER,
        ttl_seconds=settings.session_ttl_seconds,
        user_id=user.id,
        shop_id=selected.shop_id if selected else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, SESSION_COOKIE_NAME, token)
    chosen = (
        ShopSummary(
            id=selected.shop.id,
            name=selected.shop.name,
            slug=selected.shop.slug,
            role=selected.role,
        )
        if selected
        else None
    )
    return SellerAuthResponse(shop=chosen, available_shops=available)


@router.get("/me", response_model=CurrentUserResponse)
async def me(
    session: Annotated[Session, Depends(get_session)],
    db: Annotated[DbSession, Depends(get_db)],
) -> CurrentUserResponse:
    if session.principal_type is PrincipalType.CUSTOMER and session.user_id:
        user = await db.get(User, session.user_id)
        customer = await identity_service.get_or_create_customer(db, user) if user else None
        return CurrentUserResponse(
            principal_type=session.principal_type.value,
            telegram_id=user.telegram_id if user else None,
            customer_id=customer.id if customer else None,
        )
    if session.principal_type is PrincipalType.SELLER and session.user_id and session.shop_id:
        membership = await identity_service.get_membership(db, session.user_id, session.shop_id)
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        shop = await identity_service.get_shop(db, session.shop_id)
        return CurrentUserResponse(
            principal_type=session.principal_type.value,
            shop=ShopSummary(id=shop.id, name=shop.name, slug=shop.slug, role=membership.role)
            if shop
            else None,
            permissions=sorted(p.value for p in ROLE_PERMISSIONS[membership.role]),
        )
    return CurrentUserResponse(principal_type=session.principal_type.value)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[DbSession, Depends(get_db)],
) -> None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    header = request.headers.get("authorization")
    if not token and header and header.lower().startswith("bearer "):
        token = header[7:].strip()
    if token:
        await session_service.revoke_session(db, token)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def _set_session_cookie(response: Response, name: str, token: str) -> None:
    response.set_cookie(
        key=name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        domain=settings.cookie_domain,
        path="/",
    )
