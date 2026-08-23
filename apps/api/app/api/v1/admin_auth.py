"""Super Admin authentication — email + password, deliberately separate from Telegram."""
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.config import get_settings
from app.core.deps import get_current_platform_admin
from app.core.security import ADMIN_SESSION_COOKIE_NAME, verify_password
from app.db.session import get_db
from app.models.enums import PrincipalType
from app.models.identity import PlatformAdmin
from app.schemas.auth import AdminLoginRequest, AdminResponse
from app.services import session_service

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])
settings = get_settings()

_INVALID = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid email or password"
)


@router.post("/login", response_model=AdminResponse)
async def login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[DbSession, Depends(get_db)],
) -> AdminResponse:
    result = await db.execute(
        select(PlatformAdmin).where(PlatformAdmin.email == payload.email.lower())
    )
    admin = result.scalar_one_or_none()

    if admin is None or not admin.is_active:
        # Same error and comparable work either way, so the response does not reveal
        # whether the account exists.
        verify_password(payload.password, "$argon2id$v=19$m=65536,t=3,p=4$invalid$invalid")
        raise _INVALID

    now = datetime.now(UTC)
    if admin.locked_until is not None and admin.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="account temporarily locked"
        )

    if not verify_password(payload.password, admin.password_hash):
        admin.failed_login_count += 1
        if admin.failed_login_count >= settings.admin_max_failed_logins:
            admin.locked_until = now + timedelta(seconds=settings.admin_lockout_seconds)
            admin.failed_login_count = 0
        await db.commit()
        raise _INVALID

    admin.failed_login_count = 0
    admin.locked_until = None
    admin.last_login_at = now
    await db.commit()

    token = await session_service.create_session(
        db,
        principal_type=PrincipalType.PLATFORM_ADMIN,
        ttl_seconds=settings.session_ttl_seconds,
        platform_admin_id=admin.id,
        user_agent=request.headers.get("user-agent"),
    )
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        domain=settings.cookie_domain,
        path="/",
    )
    return AdminResponse(id=admin.id, email=admin.email)


@router.get("/me", response_model=AdminResponse)
async def me(
    admin: Annotated[PlatformAdmin, Depends(get_current_platform_admin)],
) -> AdminResponse:
    return AdminResponse(id=admin.id, email=admin.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[DbSession, Depends(get_db)],
) -> None:
    token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)
    if token:
        await session_service.revoke_session(db, token)
    response.delete_cookie(ADMIN_SESSION_COOKIE_NAME, path="/")
