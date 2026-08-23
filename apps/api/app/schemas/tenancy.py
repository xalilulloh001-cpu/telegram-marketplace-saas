"""Shop and membership contracts."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ShopMemberRole, ShopStatus


class ShopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    logo_url: str | None
    contact_phone: str | None
    contact_email: str | None
    address_line: str | None
    city: str | None
    status: ShopStatus
    created_at: datetime
    updated_at: datetime


class ShopUpdate(BaseModel):
    """Deliberately narrow: slug, status and plan are not seller-editable."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    logo_url: str | None = None
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_email: EmailStr | None = None
    address_line: str | None = None
    city: str | None = Field(default=None, max_length=128)


class MemberResponse(BaseModel):
    id: int
    user_id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    role: ShopMemberRole
    created_at: datetime


class MemberCreate(BaseModel):
    telegram_id: int = Field(gt=0)
    role: ShopMemberRole = ShopMemberRole.MANAGER


class MemberUpdate(BaseModel):
    role: ShopMemberRole
