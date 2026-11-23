import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings
from app.core.errors import AuthenticationError
from app.db.enums import UserRole


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    role: UserRole


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: uuid.UUID, role: UserRole | str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.jwt_access_token_expire_minutes * 60
    expire = _now() + timedelta(seconds=expires_in)
    role_value = role.value if isinstance(role, UserRole) else UserRole(role).value
    payload = {
        "sub": str(user_id),
        "role": role_value,
        "iss": settings.jwt_issuer,
        "exp": expire,
        "typ": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, expires_in


def decode_access_token(token: str) -> AccessTokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "role", "typ"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired access token.") from exc
    if payload.get("typ") != "access":
        raise AuthenticationError("Invalid access token type.")
    try:
        user_id = uuid.UUID(payload["sub"])
        role = UserRole(payload["role"])
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Invalid access token claims.") from exc
    return AccessTokenClaims(user_id=user_id, role=role)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    settings = get_settings()
    return _now() + timedelta(days=settings.jwt_refresh_token_expire_days)