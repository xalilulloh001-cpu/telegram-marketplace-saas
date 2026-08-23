"""Telegram initData verification: signature, freshness, tampering."""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.services.telegram_auth import TelegramAuthError, verify_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
MAX_AGE = 300


def build_init_data(auth_date: int | None = None, telegram_id: int = 42, **overrides) -> str:
    payload = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAF",
        "user": json.dumps({"id": telegram_id, "first_name": "Test", "username": "tester"}),
    }
    payload.update(overrides)
    check_string = "\n".join(f"{k}={payload[k]}" for k in sorted(payload))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(payload)


def test_valid_init_data_is_accepted() -> None:
    verified = verify_init_data(build_init_data(), BOT_TOKEN, MAX_AGE)
    assert verified.user.telegram_id == 42
    assert verified.user.username == "tester"


def test_invalid_hash_is_rejected() -> None:
    tampered = build_init_data().replace("hash=", "hash=0")
    with pytest.raises(TelegramAuthError):
        verify_init_data(tampered, BOT_TOKEN, MAX_AGE)


def test_tampered_user_id_is_rejected() -> None:
    """The signature covers the user payload, so swapping the id invalidates it."""
    original = build_init_data(telegram_id=42)
    tampered = original.replace("%22id%22%3A+42", "%22id%22%3A+999")
    with pytest.raises(TelegramAuthError):
        verify_init_data(tampered, BOT_TOKEN, MAX_AGE)


def test_expired_auth_date_is_rejected() -> None:
    stale = build_init_data(auth_date=int(time.time()) - (MAX_AGE + 60))
    with pytest.raises(TelegramAuthError):
        verify_init_data(stale, BOT_TOKEN, MAX_AGE)


def test_future_auth_date_is_rejected() -> None:
    future = build_init_data(auth_date=int(time.time()) + (MAX_AGE + 60))
    with pytest.raises(TelegramAuthError):
        verify_init_data(future, BOT_TOKEN, MAX_AGE)


def test_wrong_bot_token_is_rejected() -> None:
    with pytest.raises(TelegramAuthError):
        verify_init_data(build_init_data(), "999:OTHER-TOKEN", MAX_AGE)


def test_missing_bot_token_is_rejected() -> None:
    with pytest.raises(TelegramAuthError):
        verify_init_data(build_init_data(), "", MAX_AGE)
