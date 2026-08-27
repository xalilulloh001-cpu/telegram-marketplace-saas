"""Double-submit CSRF protection and cookie configuration."""
import hashlib
import hmac
import time

import pytest

from app.core.security import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME

pytestmark = pytest.mark.asyncio

BOT_TOKEN = "123456:TEST-TOKEN"


def build_login_widget(telegram_id: int = 42, auth_date: int | None = None) -> dict[str, str]:
    """Login Widget payloads are signed with SHA-256 of the bot token, not the Mini App scheme."""
    data = {
        "id": str(telegram_id),
        "first_name": "Test",
        "username": "tester",
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
    }
    check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    data["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return data


# --- CSRF -----------------------------------------------------------------

async def test_cookie_auth_with_valid_token_passes(client, seller_factory) -> None:
    ctx = await seller_factory("csrf1", 20001)
    response = await client.patch(
        "/api/v1/seller/shop",
        json={"name": "Renamed"},
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    assert response.status_code == 200


async def test_cookie_auth_without_token_is_forbidden(client, seller_factory) -> None:
    """The cookie alone is not enough — a cross-site request would carry it automatically."""
    ctx = await seller_factory("csrf2", 20002)
    response = await client.patch(
        "/api/v1/seller/shop", json={"name": "Hijacked"}, cookies=ctx["cookies"]
    )
    assert response.status_code == 403
    assert "csrf" in response.json()["detail"].lower()


async def test_cookie_auth_with_invalid_token_is_forbidden(client, seller_factory) -> None:
    ctx = await seller_factory("csrf3", 20003)
    response = await client.patch(
        "/api/v1/seller/shop",
        json={"name": "Hijacked"},
        cookies=ctx["cookies"],
        headers={"X-CSRF-Token": "not-a-real-token"},
    )
    assert response.status_code == 403


async def test_token_from_another_session_is_forbidden(client, seller_factory) -> None:
    """Tokens are derived from the session, so one session's token is useless elsewhere."""
    ctx_a = await seller_factory("csrf4a", 20004)
    ctx_b = await seller_factory("csrf4b", 20005)

    response = await client.patch(
        "/api/v1/seller/shop",
        json={"name": "Hijacked"},
        cookies=ctx_a["cookies"],
        headers=ctx_b["headers"],
    )
    assert response.status_code == 403


async def test_bearer_auth_needs_no_csrf_token(
    client, customer_factory, public_shop_factory, product_factory
) -> None:
    """The customer Mini App uses bearer tokens and must keep working untouched."""
    shop = await public_shop_factory("csrf5", 20006)
    product = await product_factory(shop.id, "Widget", stock=5)
    ctx = await customer_factory(21001)

    response = await client.post(
        f"/api/v1/customer/shops/{shop.id}/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=ctx["headers"],
    )
    assert response.status_code == 201


async def test_get_requests_need_no_csrf_token(client, seller_factory) -> None:
    ctx = await seller_factory("csrf6", 20007)
    response = await client.get("/api/v1/seller/shop", cookies=ctx["cookies"])
    assert response.status_code == 200


async def test_login_endpoints_are_exempt(client, db) -> None:
    """A session cannot exist yet, so login is protected by its own credentials."""
    from app.models.enums import ShopMemberRole
    from app.models.identity import User
    from app.models.tenancy import Shop, ShopMember
    from tests.test_telegram_auth import build_init_data

    user = User(telegram_id=20008)
    shop = Shop(name="Exempt", slug="exempt", order_prefix="E")
    db.add_all([user, shop])
    await db.commit()
    db.add(ShopMember(shop_id=shop.id, user_id=user.id, role=ShopMemberRole.OWNER))
    await db.commit()

    response = await client.post(
        "/api/v1/auth/telegram/seller",
        json={"init_data": build_init_data(telegram_id=20008)},
    )
    assert response.status_code == 200


async def test_csrf_token_is_rejected_after_logout(client, seller_factory) -> None:
    ctx = await seller_factory("csrf7", 20009)
    logout = await client.post(
        "/api/v1/auth/logout", cookies=ctx["cookies"], headers=ctx["headers"]
    )
    assert logout.status_code == 204

    response = await client.patch(
        "/api/v1/seller/shop",
        json={"name": "After logout"},
        cookies=ctx["cookies"],
        headers=ctx["headers"],
    )
    # The session is revoked, so the request cannot succeed even with a matching token.
    assert response.status_code in {401, 403}


# --- cookie configuration -------------------------------------------------

async def test_lax_cookie_attributes(client, db) -> None:
    from app.core.security import hash_password
    from app.models.identity import PlatformAdmin

    db.add(PlatformAdmin(email="cookie@example.com", password_hash=hash_password("Str0ngPass!")))
    await db.commit()

    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "cookie@example.com", "password": "Str0ngPass!"},
    )
    raw = login.headers.get_list("set-cookie")
    joined = " ".join(raw).lower()
    assert "samesite=lax" in joined
    assert CSRF_COOKIE_NAME in joined
    # The session cookie stays HttpOnly; the CSRF cookie must not be.
    session_cookie = next(c for c in raw if c.startswith("mp_admin_session="))
    csrf_cookie = next(c for c in raw if c.startswith(f"{CSRF_COOKIE_NAME}="))
    assert "httponly" in session_cookie.lower()
    assert "httponly" not in csrf_cookie.lower()


async def test_none_samesite_forces_secure(monkeypatch, client, seller_factory) -> None:
    """SameSite=None is only honoured on secure cookies, so Secure is applied regardless."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("COOKIE_SAMESITE", "none")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    get_settings.cache_clear()

    ctx = await seller_factory("csrf8", 20010)
    joined = " ".join(ctx.get("set_cookie", [])) if ctx.get("set_cookie") else ""
    del joined  # attributes are asserted through a fresh login below

    from fastapi import Response

    from app.core.cookies import set_session_cookies

    response = Response()
    set_session_cookies(response, SESSION_COOKIE_NAME, "sample-token")
    header = " ".join(response.headers.getlist("set-cookie")).lower()
    assert "samesite=none" in header
    assert "secure" in header

    get_settings.cache_clear()
    monkeypatch.delenv("COOKIE_SAMESITE", raising=False)
    monkeypatch.setenv("COOKIE_SAMESITE", "lax")
    get_settings.cache_clear()


# --- CSRF secret configuration --------------------------------------------

def test_production_without_csrf_secret_fails_validation() -> None:
    """A production deployment must not start with weak CSRF protection."""
    import pydantic

    from app.core.config import Settings

    with pytest.raises(pydantic.ValidationError) as excinfo:
        Settings(app_env="production", csrf_secret=None, telegram_bot_token="123456:SOME-TOKEN")

    message = str(excinfo.value)
    assert "CSRF_SECRET" in message
    # The error explains the fix without ever echoing a secret value.
    assert "123456:SOME-TOKEN" not in message


def test_production_with_csrf_secret_is_accepted() -> None:
    from app.core.config import Settings

    settings = Settings(app_env="production", csrf_secret="a-real-production-secret")
    assert settings.csrf_signing_key == "a-real-production-secret"


def test_bot_token_is_never_used_as_csrf_key() -> None:
    """Rotating the Telegram bot token must not change CSRF signing, and the token must
    never become the signing key."""
    from app.core.config import Settings

    first = Settings(app_env="development", csrf_secret=None, telegram_bot_token="111:AAA")
    second = Settings(app_env="development", csrf_secret=None, telegram_bot_token="999:ZZZ")

    assert first.csrf_signing_key == second.csrf_signing_key
    assert "111:AAA" not in first.csrf_signing_key
    assert "999:ZZZ" not in second.csrf_signing_key


def test_explicit_secret_survives_bot_token_change() -> None:
    from app.core.config import Settings
    from app.core.security import build_csrf_token

    before = Settings(app_env="staging", csrf_secret="stable-secret", telegram_bot_token="111:AAA")
    after = Settings(app_env="staging", csrf_secret="stable-secret", telegram_bot_token="999:ZZZ")

    token_before = build_csrf_token("session-token", before.csrf_signing_key)
    token_after = build_csrf_token("session-token", after.csrf_signing_key)
    assert token_before == token_after


def test_development_default_is_not_used_in_production() -> None:
    from app.core.config import DEVELOPMENT_CSRF_SECRET, Settings

    dev = Settings(app_env="development", csrf_secret=None)
    assert dev.csrf_signing_key == DEVELOPMENT_CSRF_SECRET

    prod = Settings(app_env="production", csrf_secret="real")
    assert prod.csrf_signing_key != DEVELOPMENT_CSRF_SECRET
