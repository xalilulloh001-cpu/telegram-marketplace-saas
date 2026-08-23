"""Password hashing and opaque session token primitives."""
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

_hasher = PasswordHasher()

SESSION_COOKIE_NAME = "mp_session"
ADMIN_SESSION_COOKIE_NAME = "mp_admin_session"


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
