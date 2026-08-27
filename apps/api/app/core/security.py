"""Password hashing and opaque session token primitives."""
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

_hasher = PasswordHasher()

SESSION_COOKIE_NAME = "mp_session"
ADMIN_SESSION_COOKIE_NAME = "mp_admin_session"
CSRF_COOKIE_NAME = "mp_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError:
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    """Sessions are looked up by digest, never by the raw token."""
    return hashlib.sha256(token.encode()).hexdigest()


def build_csrf_token(session_token: str, signing_key: str) -> str:
    """Derives the CSRF token from the session token.

    Deriving rather than storing means no extra column and no lookup: the server can
    recompute the expected value from the session cookie it already received. The token
    is therefore bound to one session — replaying another session's token fails.
    """
    return hmac.new(
        signing_key.encode(), hash_session_token(session_token).encode(), hashlib.sha256
    ).hexdigest()


def verify_csrf_token(session_token: str, presented: str, signing_key: str) -> bool:
    return hmac.compare_digest(build_csrf_token(session_token, signing_key), presented)
