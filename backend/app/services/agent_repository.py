import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.schemas.plan import TaskPlan
from app.agent.state_machine import transition
from app.db.enums import ExecutionStatus, StepStatus, TaskStatus, ToolExecutionStatus
from app.db.models.agent_execution import AgentExecution
from app.db.models.agent_task import AgentTask
from app.db.models.task_step import TaskStep
from app.db.models.tool_execution import ToolExecution


async def load_task(session: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID) -> AgentTask | None:
    statement = (
        select(AgentTask)
        .where(AgentTask.id == task_id, AgentTask.user_id == user_id)
        .options(selectinload(AgentTask.steps), selectinload(AgentTask.approval_requests))
    )
    return await session.scalar(statement)


def _coerce_status(value: TaskStatus | str) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    return TaskStatus(value)


async def set_status(
    session: AsyncSession,
    task: AgentTask,
    status: TaskStatus,
    *,
    message: str | None = None,
) -> None:
    transition(_coerce_status(task.status), status)
    task.status = status
    if message is not None:
        task.outcome_message = message
    await session.flush()


async def persist_intent(session: AsyncSession, task: AgentTask, intent_json: str) -> None:
    task.intent_json = intent_json
    await session.flush()


async def persist_plan(session: AsyncSession, task: AgentTask, plan: TaskPlan) -> list[TaskStep]:
    task.plan_json = plan.model_dump_json()
    await session.execute(delete(TaskStep).where(TaskStep.task_id == task.id))
    await session.flush()
    rows: list[TaskStep] = []
    for spec in plan.steps:
        row = TaskStep(
            task_id=task.id,
            sequence=spec.sequence,
            description=spec.description,
            tool_name=spec.tool_name,
            arguments_json=json.dumps(spec.arguments),
            status=StepStatus.PLANNED,
        )
        session.add(row)
        rows.append(row)
    await session.flush()
    return rows


async def start_execution_record(session: AsyncSession, task: AgentTask) -> AgentExecution:
    record = AgentExecution(
        task_id=task.id,
        status=ExecutionStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    session.add(record)
    await session.flush()
    return record


async def finish_execution_record(
    session: AsyncSession,
    record: AgentExecution,
    *,
    status: ExecutionStatus,
    message: str | None,
) -> None:
    record.status = status
    record.outcome_message = message
    record.ended_at = datetime.now(timezone.utc)
    await session.flush()


async def record_tool_run(
    session: AsyncSession,
    *,
    task: AgentTask,
    step: TaskStep,
    tool_name: str,
    arguments: dict,
    status: ToolExecutionStatus,
    result: str | None,
) -> ToolExecution:
    row = ToolExecution(
        task_id=task.id,
        step_id=step.id,
        tool_name=tool_name,
        status=status,
        arguments_json=json.dumps(arguments),
        result_json=result,
    )
    session.add(row)
    current = step.status if isinstance(step.status, StepStatus) else StepStatus(step.status)
    if current is not StepStatus.SKIPPED:
        step.status = StepStatus.COMPLETED if status is ToolExecutionStatus.SUCCEEDED else StepStatus.FAILED
    await session.flush()
    return row


async def refresh_cancel_pause(session: AsyncSession, task: AgentTask) -> AgentTask:
    await session.refresh(task)
    return task

