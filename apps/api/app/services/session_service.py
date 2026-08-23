"""Server-side session lifecycle. Sessions are opaque and revocable at any time."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.core.security import generate_session_token, hash_session_token
from app.models.auth import Session, TelegramAuthNonce
from app.models.enums import PrincipalType


async def create_session(
    db: DbSession,
    principal_type: PrincipalType,
    ttl_seconds: int,
    user_id: int | None = None,
    platform_admin_id: int | None = None,
    shop_id: int | None = None,
    user_agent: str | None = None,
) -> str:
    """Returns the raw token — it is never stored and cannot be recovered later."""
    token = generate_session_token()
    db.add(
        Session(
            token_hash=hash_session_token(token),
            principal_type=principal_type,
            user_id=user_id,
            platform_admin_id=platform_admin_id,
            shop_id=shop_id,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
            user_agent=user_agent,
        )
    )
    await db.commit()
    return token


async def resolve_session(db: DbSession, token: str) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.token_hash == hash_session_token(token))
    )
    session = result.scalar_one_or_none()
    if session is None or session.revoked_at is not None:
        return None
    if session.expires_at <= datetime.now(UTC):
        return None
    return session


async def revoke_session(db: DbSession, token: str) -> None:
    session = await resolve_session(db, token)
    if session is not None:
        session.revoked_at = datetime.now(UTC)
        await db.commit()


async def consume_telegram_nonce(db: DbSession, init_data_hash: str, ttl_seconds: int) -> bool:
    """False when this exact initData payload was already used — replay protection."""
    now = datetime.now(UTC)
    await db.execute(delete(TelegramAuthNonce).where(TelegramAuthNonce.expires_at <= now))
    existing = await db.execute(
        select(TelegramAuthNonce).where(TelegramAuthNonce.init_data_hash == init_data_hash)
    )
    if existing.scalar_one_or_none() is not None:
        await db.commit()
        return False
    db.add(
        TelegramAuthNonce(
            init_data_hash=init_data_hash, expires_at=now + timedelta(seconds=ttl_seconds)
        )
    )
    await db.commit()
    return True
