from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.core.errors import AppError, NotFoundError
from app.db.models.user import User
from app.db.session import get_db_session
from app.memory.errors import MemoryPolicyError
from app.memory.service import MemoryService
from app.schemas.memory import ClearTaskMemoryResponse, TaskMemoryResponse, UserPreferencesResponse, UserPreferencesUpdateRequest
from app.services import task_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["memory"])


@router.get("/api/tasks/{task_id}/memory", response_model=TaskMemoryResponse)
async def get_task_memory(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskMemoryResponse:
    task = await task_service.get_task(session, current_user, task_id)
    if task is None:
        raise NotFoundError("Task not found.")
    bundle = await MemoryService(session).get_task_memory(current_user, task)
    return TaskMemoryResponse.model_validate(bundle.model_dump())


@router.delete("/api/tasks/{task_id}/memory", response_model=ClearTaskMemoryResponse)
async def clear_task_memory(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ClearTaskMemoryResponse:
    task = await task_service.get_task(session, current_user, task_id)
    if task is None:
        raise NotFoundError("Task not found.")
    try:
        removed = await MemoryService(session).clear_task_memory(current_user, task)
    except MemoryPolicyError as exc:
        raise AppError(code=exc.code, message=exc.message, status_code=403) from exc
    return ClearTaskMemoryResponse(removed_entries=removed, task_id=str(task_id))


@router.get("/api/users/me/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserPreferencesResponse:
    prefs = await MemoryService(session).get_preferences(current_user)
    return UserPreferencesResponse(preferences=prefs)


@router.patch("/api/users/me/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    body: UserPreferencesUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserPreferencesResponse:
    try:
        prefs = await MemoryService(session).update_preferences(current_user, body.preferences)
    except MemoryPolicyError as exc:
        raise AppError(code=exc.code, message=exc.message, status_code=400) from exc
    return UserPreferencesResponse(preferences=prefs)