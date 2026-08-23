"""Server-side verification of Telegram Mini App initData.

Implements the algorithm from Telegram's WebApp documentation: the payload is signed
with a key derived from the bot token, so a client cannot forge it and the bot token
itself never leaves the server.
"""
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class TelegramAuthError(Exception):
    """Raised when initData cannot be trusted."""


@dataclass(frozen=True)
class TelegramUser:
    telegram_id: int
    first_name: str | None
    last_name: str | None
    username: str | None


@dataclass(frozen=True)
class VerifiedInitData:
    user: TelegramUser
    auth_date: int
    hash: str


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def verify_init_data(init_data: str, bot_token: str, max_age_seconds: int) -> VerifiedInitData:
    if not bot_token:
        raise TelegramAuthError("bot token is not configured")
    if not init_data:
        raise TelegramAuthError("init data is empty")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("init data has no hash")

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    expected_hash = hmac.new(
        _secret_key(bot_token), data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramAuthError("init data signature mismatch")

    raw_auth_date = pairs.get("auth_date")
    if not raw_auth_date or not raw_auth_date.isdigit():
        raise TelegramAuthError("init data has no valid auth_date")
    auth_date = int(raw_auth_date)
    age = int(time.time()) - auth_date
    if age > max_age_seconds:
        raise TelegramAuthError("init data has expired")
    if age < -max_age_seconds:
        raise TelegramAuthError("init data auth_date is in the future")

    raw_user = pairs.get("user")
    if not raw_user:
        raise TelegramAuthError("init data has no user")
    try:
        parsed = json.loads(raw_user)
        telegram_id = int(parsed["id"])
    except (ValueError, KeyError, TypeError) as exc:
        raise TelegramAuthError("init data user payload is malformed") from exc

    return VerifiedInitData(
        user=TelegramUser(
            telegram_id=telegram_id,
            first_name=parsed.get("first_name"),
            last_name=parsed.get("last_name"),
            username=parsed.get("username"),
        ),
        auth_date=auth_date,
        hash=received_hash,
    )
