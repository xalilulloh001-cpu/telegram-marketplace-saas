"""Double-submit CSRF protection for cookie-authenticated requests.

Only cookie-authenticated state-changing requests are checked. A bearer token cannot be
attached to a cross-site request without a CORS preflight our origin list would reject,
so the customer Mini App needs no CSRF token and is deliberately left untouched.
"""
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.status import HTTP_403_FORBIDDEN

from app.core.config import get_settings
from app.core.security import (
    ADMIN_SESSION_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    verify_csrf_token,
)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Endpoints that create a session: no CSRF token can exist yet. They are protected by
# their own credentials instead — a Telegram signature or the admin password.
EXEMPT_PATHS = frozenset(
    {
        "/api/v1/auth/telegram",
        "/api/v1/auth/telegram/seller",
        "/api/v1/admin/auth/login",
    }
)


def _session_cookie(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE_NAME) or request.cookies.get(
        ADMIN_SESSION_COOKIE_NAME
    )


def _has_bearer(request: Request) -> bool:
    header = request.headers.get("authorization", "")
    return header.lower().startswith("bearer ")


async def csrf_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if request.method in SAFE_METHODS or request.url.path in EXEMPT_PATHS:
        return await call_next(request)

    session_token = _session_cookie(request)
    # No cookie, or a bearer token in play: this request is not CSRF-exposed.
    if session_token is None or _has_bearer(request):
        return await call_next(request)

    presented = request.headers.get(CSRF_HEADER_NAME) or request.cookies.get(CSRF_COOKIE_NAME)
    if not request.headers.get(CSRF_HEADER_NAME):
        # The cookie alone proves nothing — a cross-site request carries it automatically.
        # Only the header, which an attacker's origin cannot read, counts.
        presented = None

    if not presented or not verify_csrf_token(
        session_token, presented, get_settings().csrf_signing_key
    ):
        return JSONResponse(
            status_code=HTTP_403_FORBIDDEN, content={"detail": "csrf token missing or invalid"}
        )

    return await call_next(request)
