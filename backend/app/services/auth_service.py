import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import (
    TokenPair,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.core.errors import AuthenticationError, ConflictError
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User
from app.services.audit_service import record_audit


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
) -> tuple[User, TokenPair]:
    normalized = email.strip().lower()
    existing = await session.scalar(select(User).where(User.email == normalized))
    if existing is not None:
        raise ConflictError("An account with this email already exists.")
    user = User(
        email=normalized,
        password_hash=hash_password(password),
        display_name=display_name.strip(),
    )
    session.add(user)
    await session.flush()
    await record_audit(
        session,
        action="user.register",
        resource_type="user",
        user_id=user.id,
        resource_id=str(user.id),
    )
    tokens = await issue_token_pair(session, user)
    return user, tokens


async def authenticate_user(session: AsyncSession, *, email: str, password: str) -> User:
    normalized = email.strip().lower()
    user = await session.scalar(select(User).where(User.email == normalized))
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationError("User account is inactive.")
    return user


async def issue_token_pair(session: AsyncSession, user: User) -> TokenPair:
    access_token, expires_in = create_access_token(user.id, user.role)
    refresh_token = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_token_expiry(),
        )
    )
    await session.flush()
    return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in)


async def login_user(session: AsyncSession, *, email: str, password: str) -> tuple[User, TokenPair]:
    user = await authenticate_user(session, email=email, password=password)
    await record_audit(
        session,
        action="user.login",
        resource_type="user",
        user_id=user.id,
        resource_id=str(user.id),
    )
    tokens = await issue_token_pair(session, user)
    return user, tokens


async def refresh_tokens(session: AsyncSession, *, refresh_token: str) -> tuple[User, TokenPair]:
    token_hash = hash_refresh_token(refresh_token)
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
    )
    if row is None:
        raise AuthenticationError("Invalid refresh token.")
    from datetime import datetime, timezone

    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise AuthenticationError("Refresh token has expired.")
    user = await session.scalar(select(User).where(User.id == row.user_id))
    if user is None or not user.is_active:
        raise AuthenticationError("User account is inactive or missing.")
    row.revoked_at = datetime.now(timezone.utc)
    tokens = await issue_token_pair(session, user)
    await record_audit(
        session,
        action="user.refresh",
        resource_type="user",
        user_id=user.id,
        resource_id=str(user.id),
    )
    return user, tokens


async def logout_user(session: AsyncSession, *, user_id: uuid.UUID, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    row = await session.scalar(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    if row is not None:
        from datetime import datetime, timezone

        row.revoked_at = datetime.now(timezone.utc)
    await record_audit(
        session,
        action="user.logout",
        resource_type="user",
        user_id=user_id,
        resource_id=str(user_id),
    )