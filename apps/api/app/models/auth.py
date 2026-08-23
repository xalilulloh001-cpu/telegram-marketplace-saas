"""Server-side session store and Telegram replay protection."""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import PrincipalType


class Session(Base, TimestampMixin):
    """Opaque server-side session. Only the SHA-256 of the token is stored, so a
    database leak does not hand out usable sessions."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    principal_type: Mapped[PrincipalType] = mapped_column(
        Enum(PrincipalType, name="principal_type"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    platform_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("platform_admins.id", ondelete="CASCADE")
    )
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_expires_at", "expires_at"),
    )


class TelegramAuthNonce(Base):
    """One row per accepted initData payload — the unique hash makes replay impossible
    inside the auth_date validity window. Rows are pruned once expired."""

    __tablename__ = "telegram_auth_nonces"

    id: Mapped[int] = mapped_column(primary_key=True)
    init_data_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_telegram_auth_nonces_expires_at", "expires_at"),)
