from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.errors import NotFoundError
from app.db.models.agent_task import AgentTask
from app.db.models.user import User
from app.db.session import get_db_session
from app.agent.orchestrator import AgentOrchestrator
from app.schemas.agent import RunTaskResponse
from app.schemas.approval import ApprovalDecisionRequest, PendingApprovalsResponse
from app.schemas.task import (
    AgentTaskDetailResponse,
    AgentTaskResponse,
    ApprovalRequestResponse,
    TaskCreateRequest,
)
from app.safety.approval_service import list_pending_approvals
from app.services import task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=AgentTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTask:
    return await task_service.create_task(session, current_user, instruction=body.instruction)


@router.get("", response_model=list[AgentTaskResponse])
async def list_tasks(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AgentTask]:
    return await task_service.list_tasks(session, current_user)


@router.get("/{task_id}", response_model=AgentTaskDetailResponse)
async def get_task(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTask:
    task = await task_service.get_task(session, current_user, task_id)
    if task is None:
        raise NotFoundError("Task not found.")
    return task


@router.post("/{task_id}/run", response_model=RunTaskResponse)
async def run_task(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RunTaskResponse:
    task = await task_service.get_task(session, current_user, task_id)
    if task is None:
        raise NotFoundError("Task not found.")
    outcome = await AgentOrchestrator(session).run_task(current_user, task_id)
    await session.refresh(task)
    return RunTaskResponse(task_id=task.id, status=task.status, outcome=outcome)


@router.post("/{task_id}/resume", response_model=RunTaskResponse)
async def resume_task(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RunTaskResponse:
    task = await task_service.get_task(session, current_user, task_id)
    if task is None:
        raise NotFoundError("Task not found.")
    outcome = await AgentOrchestrator(session).run_task(current_user, task_id, resume=True)
    await session.refresh(task)
    return RunTaskResponse(task_id=task.id, status=task.status, outcome=outcome)


@router.post("/{task_id}/cancel", response_model=AgentTaskResponse)
async def cancel_task(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTask:
    task = await AgentOrchestrator(session).cancel_task(current_user, task_id)
    await session.refresh(task)
    return task


@router.get("/{task_id}/approvals", response_model=PendingApprovalsResponse)
async def list_task_approvals(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PendingApprovalsResponse:
    task = await task_service.get_task(session, current_user, task_id)
    if task is None:
        raise NotFoundError("Task not found.")
    pending = await list_pending_approvals(session, task, current_user.id)
    return PendingApprovalsResponse(task_id=task.id, approvals=pending)


@router.post("/{task_id}/approve", response_model=AgentTaskResponse)
async def approve_task(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTask:
    task = await AgentOrchestrator(session).approve_task(current_user, task_id)
    await session.refresh(task)
    return task


@router.post("/{task_id}/approvals/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_single_request(
    task_id: UUID,
    approval_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    from app.safety.approval_service import approve_request

    task = await task_service.get_task(session, current_user, task_id)
    if task is None:
        raise NotFoundError("Task not found.")
    row = await approve_request(session, current_user, approval_id)
    return row


@router.post("/{task_id}/approvals/{approval_id}/reject", response_model=AgentTaskResponse)
async def reject_approval_request(
    task_id: UUID,
    approval_id: UUID,
    body: ApprovalDecisionRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTask:
    task = await AgentOrchestrator(session).reject_approval(
        current_user, task_id, approval_id, reason=body.reason
    )
    await session.refresh(task)
    return task
