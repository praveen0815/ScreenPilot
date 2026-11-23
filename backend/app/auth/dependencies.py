from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import can_access_task
from app.auth.tokens import decode_access_token
from app.core.errors import AuthenticationError, ForbiddenError, NotFoundError
from app.db.models.agent_task import AgentTask
from app.db.models.user import User
from app.db.session import get_db_session

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError()
    claims = decode_access_token(credentials.credentials)
    user = await session.scalar(select(User).where(User.id == claims.user_id))
    if user is None or not user.is_active:
        raise AuthenticationError("User account is inactive or missing.")
    return user


async def get_task_for_current_user(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgentTask:
    from uuid import UUID

    try:
        parsed_id = UUID(task_id)
    except ValueError as exc:
        raise NotFoundError("Task not found.") from exc
    task = await session.scalar(select(AgentTask).where(AgentTask.id == parsed_id))
    if task is None:
        raise NotFoundError("Task not found.")
    if not can_access_task(current_user, task):
        raise ForbiddenError()
    return task