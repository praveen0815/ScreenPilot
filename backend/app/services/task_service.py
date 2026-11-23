import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import TaskStatus
from app.db.models.agent_task import AgentTask
from app.db.models.user import User
from app.services.audit_service import record_audit


async def create_task(session: AsyncSession, user: User, *, instruction: str) -> AgentTask:
    task = AgentTask(user_id=user.id, instruction=instruction.strip(), status=TaskStatus.PENDING)
    session.add(task)
    await session.flush()
    await record_audit(
        session,
        action="task.create",
        resource_type="agent_task",
        user_id=user.id,
        task_id=task.id,
        resource_id=str(task.id),
    )
    return task


async def list_tasks(session: AsyncSession, user: User) -> list[AgentTask]:
    statement = (
        select(AgentTask)
        .where(AgentTask.user_id == user.id)
        .order_by(AgentTask.created_at.desc())
    )
    return list((await session.scalars(statement)).all())


async def get_task(session: AsyncSession, user: User, task_id: uuid.UUID) -> AgentTask | None:
    statement = (
        select(AgentTask)
        .where(AgentTask.id == task_id, AgentTask.user_id == user.id)
        .options(
            selectinload(AgentTask.steps),
            selectinload(AgentTask.agent_executions),
            selectinload(AgentTask.tool_executions),
            selectinload(AgentTask.approval_requests),
        )
    )
    return await session.scalar(statement)