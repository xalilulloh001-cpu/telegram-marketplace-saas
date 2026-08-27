"""Session and CSRF cookie handling, driven entirely by configuration.

SameSite is not hard-coded: locally the frontends and the API share the localhost site so
"lax" is enough, while in production they are cross-site and require "none" with Secure.
"""
from typing import Literal, cast

from fastapi import Response

from app.core.config import get_settings
from app.core.security import CSRF_COOKIE_NAME, build_csrf_token


def _samesite() -> Literal["lax", "strict", "none"]:
    value = get_settings().cookie_samesite.lower()
    if value not in {"lax", "strict", "none"}:
        value = "lax"
    return cast(Literal["lax", "strict", "none"], value)


def set_session_cookies(response: Response, cookie_name: str, token: str) -> None:
    settings = get_settings()
    samesite = _samesite()
    # SameSite=None is only honoured on secure cookies; browsers drop it otherwise.
    secure = settings.cookie_secure or samesite == "none"

    response.set_cookie(
        key=cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=secure,
        samesite=samesite,
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=build_csrf_token(token, settings.csrf_signing_key),
        max_age=settings.session_ttl_seconds,
        # Deliberately readable by JavaScript: the frontend must copy it into a header,
        # which is exactly what a cross-site attacker cannot do.
        httponly=False,
        secure=secure,
        samesite=samesite,
        domain=settings.cookie_domain,
        path="/",
    )


def clear_session_cookies(response: Response, cookie_name: str) -> None:
    settings = get_settings()
    response.delete_cookie(cookie_name, path="/", domain=settings.cookie_domain)
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", domain=settings.cookie_domain)
