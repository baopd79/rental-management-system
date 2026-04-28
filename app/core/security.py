from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from jose import jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash password using bcrypt (cost=12)."""
    return cast(str, pwd_context.hash(plain))


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against bcrypt hash. Returns False on bad format."""
    try:
        return bool(pwd_context.verify(plain, hashed))
    except (UnknownHashError, ValueError):
        return False


def create_access_token(user_id: UUID, role: str) -> str:
    """Create signed JWT access token (HS256, TTL from settings)."""
    settings = get_settings()
    now = int(datetime.now(UTC).timestamp())
    ttl_seconds = settings.jwt_access_token_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode JWT, raise jose.JWTError if invalid/expired."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
