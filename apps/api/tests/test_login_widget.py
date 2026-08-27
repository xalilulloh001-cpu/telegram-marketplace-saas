"""Telegram Login Widget verification and seller browser sign-in."""
import time

import pytest

from app.models.enums import ShopMemberRole
from app.models.identity import User
from app.models.tenancy import Shop, ShopMember
from app.services.telegram_auth import TelegramAuthError, verify_init_data, verify_login_widget
from tests.test_csrf import BOT_TOKEN, build_login_widget
from tests.test_telegram_auth import build_init_data

pytestmark = pytest.mark.asyncio

MAX_AGE = 300


async def _seed_member(db, slug: str, telegram_id: int) -> Shop:
    user = User(telegram_id=telegram_id)
    shop = Shop(name=slug.title(), slug=slug, order_prefix=slug[0].upper())
    db.add_all([user, shop])
    await db.commit()
    db.add(ShopMember(shop_id=shop.id, user_id=user.id, role=ShopMemberRole.OWNER))
    await db.commit()
    return shop


# --- unit -----------------------------------------------------------------

def test_valid_signature_accepted() -> None:
    verified = verify_login_widget(build_login_widget(telegram_id=777), BOT_TOKEN, MAX_AGE)
    assert verified.user.telegram_id == 777
    assert verified.user.username == "tester"


def test_invalid_hash_rejected() -> None:
    payload = build_login_widget()
    payload["hash"] = "0" * 64
    with pytest.raises(TelegramAuthError):
        verify_login_widget(payload, BOT_TOKEN, MAX_AGE)


def test_tampered_id_rejected() -> None:
    """The signature covers the id, so raising privileges by editing it fails."""
    payload = build_login_widget(telegram_id=1)
    payload["id"] = "999"
    with pytest.raises(TelegramAuthError):
        verify_login_widget(payload, BOT_TOKEN, MAX_AGE)


def test_expired_auth_date_rejected() -> None:
    payload = build_login_widget(auth_date=int(time.time()) - (MAX_AGE + 60))
    with pytest.raises(TelegramAuthError):
        verify_login_widget(payload, BOT_TOKEN, MAX_AGE)


def test_future_auth_date_rejected() -> None:
    payload = build_login_widget(auth_date=int(time.time()) + (MAX_AGE + 60))
    with pytest.raises(TelegramAuthError):
        verify_login_widget(payload, BOT_TOKEN, MAX_AGE)


def test_missing_bot_token_rejected() -> None:
    with pytest.raises(TelegramAuthError):
        verify_login_widget(build_login_widget(), "", MAX_AGE)


def test_widget_payload_fails_mini_app_verifier() -> None:
    """The two schemes derive their keys differently and must never cross-validate."""
    payload = build_login_widget()
    as_query = "&".join(f"{k}={v}" for k, v in payload.items())
    with pytest.raises(TelegramAuthError):
        verify_init_data(as_query, BOT_TOKEN, MAX_AGE)


def test_mini_app_payload_fails_widget_verifier() -> None:
    from urllib.parse import parse_qsl

    init_data = build_init_data(telegram_id=55)
    with pytest.raises(TelegramAuthError):
        verify_login_widget(dict(parse_qsl(init_data)), BOT_TOKEN, MAX_AGE)


# --- endpoint -------------------------------------------------------------

async def test_seller_login_via_widget(client, db) -> None:
    shop = await _seed_member(db, "widgetshop", 30001)
    response = await client.post(
        "/api/v1/auth/telegram/seller",
        json={"login_widget": build_login_widget(telegram_id=30001)},
    )
    assert response.status_code == 200
    assert response.json()["shop"]["slug"] == shop.slug
    assert "mp_session" in response.cookies
    assert "mp_csrf" in response.cookies


async def test_widget_login_without_membership_forbidden(client) -> None:
    response = await client.post(
        "/api/v1/auth/telegram/seller",
        json={"login_widget": build_login_widget(telegram_id=30002)},
    )
    assert response.status_code == 403


async def test_widget_login_with_bad_hash_unauthorized(client, db) -> None:
    await _seed_member(db, "badhash", 30003)
    payload = build_login_widget(telegram_id=30003)
    payload["hash"] = "f" * 64
    response = await client.post(
        "/api/v1/auth/telegram/seller", json={"login_widget": payload}
    )
    assert response.status_code == 401


async def test_widget_login_replay_rejected(client, db) -> None:
    await _seed_member(db, "replayshop", 30004)
    payload = build_login_widget(telegram_id=30004)

    first = await client.post("/api/v1/auth/telegram/seller", json={"login_widget": payload})
    second = await client.post("/api/v1/auth/telegram/seller", json={"login_widget": payload})
    assert first.status_code == 200
    assert second.status_code == 401


async def test_mini_app_login_still_works_for_sellers(client, db) -> None:
    """Both Telegram surfaces remain valid entry points for a seller."""
    await _seed_member(db, "miniappshop", 30005)
    response = await client.post(
        "/api/v1/auth/telegram/seller",
        json={"init_data": build_init_data(telegram_id=30005)},
    )
    assert response.status_code == 200


async def test_both_credentials_rejected(client) -> None:
    response = await client.post(
        "/api/v1/auth/telegram/seller",
        json={
            "init_data": build_init_data(telegram_id=30006),
            "login_widget": build_login_widget(telegram_id=30006),
        },
    )
    assert response.status_code == 422


async def test_no_credential_rejected(client) -> None:
    response = await client.post("/api/v1/auth/telegram/seller", json={})
    assert response.status_code == 422


async def test_widget_session_is_seller_realm(client, db) -> None:
    """A widget session must not double as a customer credential."""
    await _seed_member(db, "realmshop", 30007)
    login = await client.post(
        "/api/v1/auth/telegram/seller",
        json={"login_widget": build_login_widget(telegram_id=30007)},
    )
    cookies = dict(login.cookies)
    response = await client.get("/api/v1/customer/orders", cookies=cookies)
    assert response.status_code == 403
