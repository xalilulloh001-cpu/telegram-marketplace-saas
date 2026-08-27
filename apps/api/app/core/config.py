"""Centralized application configuration, loaded from environment variables."""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Fixed, obviously non-secret value for local development and tests. It is never used
# when APP_ENV=production, where the validator refuses to start without a real secret.
DEVELOPMENT_CSRF_SECRET = "development-only-csrf-key-do-not-use-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_name: str = "telegram-marketplace-api"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/marketplace"

    telegram_bot_token: str | None = None
    telegram_bot_username: str | None = None

    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002"

    r2_endpoint_url: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket_name: str | None = None
    r2_public_base_url: str | None = None

    session_ttl_seconds: int = 60 * 60 * 12
    telegram_auth_max_age_seconds: int = 300
    cookie_secure: bool = True
    cookie_domain: str | None = None
    # "lax" locally (frontend and API share the localhost site); "none" in production,
    # where the Vercel frontends and the Railway API are cross-site.
    cookie_samesite: str = "lax"
    # Secret behind the double-submit CSRF token. Required in production; there is no
    # fallback to any other secret, so CSRF tokens stay independent of Telegram
    # credentials and rotating the bot token never invalidates live sessions.
    csrf_secret: str | None = None
    admin_max_failed_logins: int = 5
    admin_lockout_seconds: int = 900

    @model_validator(mode="after")
    def require_csrf_secret_in_production(self) -> "Settings":
        if self.is_production and not self.csrf_secret:
            raise ValueError(
                "CSRF_SECRET must be set when APP_ENV=production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"production", "prod"}

    @property
    def csrf_signing_key(self) -> str:
        """Never derived from another secret — a shared key would tie CSRF validity to
        Telegram credential rotation and widen the blast radius of a leak."""
        if self.csrf_secret:
            return self.csrf_secret
        if self.is_production:  # pragma: no cover - blocked by the validator above
            raise RuntimeError("CSRF_SECRET is required in production")
        return DEVELOPMENT_CSRF_SECRET

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
