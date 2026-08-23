"""Auth request/response contracts."""
from pydantic import BaseModel, EmailStr, Field

from app.models.enums import ShopMemberRole


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1)
    shop_id: int | None = Field(
        default=None,
        description="Candidate only — the server accepts it solely after verifying membership.",
    )


class ShopSummary(BaseModel):
    id: int
    name: str
    slug: str
    role: ShopMemberRole


class CustomerAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    telegram_id: int
    customer_id: int


class SellerAuthResponse(BaseModel):
    shop: ShopSummary | None
    available_shops: list[ShopSummary]


class CurrentUserResponse(BaseModel):
    principal_type: str
    telegram_id: int | None = None
    customer_id: int | None = None
    shop: ShopSummary | None = None
    permissions: list[str] = []


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class AdminResponse(BaseModel):
    id: int
    email: str
