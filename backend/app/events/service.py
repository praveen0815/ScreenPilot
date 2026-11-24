import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import agent_execution_id_var, task_id_var, tool_execution_id_var
from app.db.models.task_event import TaskEvent
from app.events.broker import get_task_event_broker
from app.events.schemas import TaskEventPayload, TaskEventType, TaskEventWire, sanitize_payload

logger = logging.getLogger("app.events")


async def _next_sequence(session: AsyncSession, task_id: uuid.UUID) -> int:
    current = await session.scalar(
        select(func.coalesce(func.max(TaskEvent.sequence), 0)).where(TaskEvent.task_id == task_id)
    )
    return int(current or 0) + 1


def _to_wire(row: TaskEvent) -> TaskEventWire:
    try:
        raw = json.loads(row.payload_json or "{}")
    except json.JSONDecodeError:
        raw = {}
    payload = TaskEventPayload.model_validate(raw)
    return TaskEventWire(
        id=row.id,
        task_id=row.task_id,
        user_id=row.user_id,
        type=TaskEventType(row.event_type),
        sequence=row.sequence,
        occurred_at=row.occurred_at,
        agent_execution_id=row.agent_execution_id,
        tool_execution_id=row.tool_execution_id,
        payload=payload,
    )


async def publish_task_event(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    event_type: TaskEventType,
    payload: dict[str, Any] | None = None,
    agent_execution_id: uuid.UUID | None = None,
    tool_execution_id: uuid.UUID | None = None,
) -> TaskEventWire:
    safe = sanitize_payload(payload)
    allowed = set(TaskEventPayload.model_fields)
    filtered = {key: value for key, value in safe.items() if key in allowed}
    validated = TaskEventPayload.model_validate(filtered)
    sequence = await _next_sequence(session, task_id)
    occurred_at = datetime.now(timezone.utc)
    row = TaskEvent(
        task_id=task_id,
        user_id=user_id,
        event_type=event_type.value,
        sequence=sequence,
        occurred_at=occurred_at,
        agent_execution_id=agent_execution_id,
        tool_execution_id=tool_execution_id,
        payload_json=validated.model_dump_json(),
    )
    session.add(row)
    await session.flush()
    wire = _to_wire(row)
    await get_task_event_broker().publish(user_id, wire)

    token_task = task_id_var.set(str(task_id))
    token_agent = agent_execution_id_var.set(str(agent_execution_id) if agent_execution_id else None)
    token_tool = tool_execution_id_var.set(str(tool_execution_id) if tool_execution_id else None)
    try:
        logger.info(
            "task_event_published",
            extra={
                "event_type": event_type.value,
                "event_id": str(wire.id),
                "task_id": str(task_id),
                "user_id": str(user_id),
                "sequence": sequence,
                "agent_execution_id": str(agent_execution_id) if agent_execution_id else None,
                "tool_execution_id": str(tool_execution_id) if tool_execution_id else None,
            },
        )
    finally:
        task_id_var.reset(token_task)
        agent_execution_id_var.reset(token_agent)
        tool_execution_id_var.reset(token_tool)
    return wire


async def list_task_events(
    session: AsyncSession,
    *,
    task_id: uuid.UUID,
    after_sequence: int = 0,
    limit: int = 100,
) -> list[TaskEventWire]:
    rows = (
        await session.scalars(
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id, TaskEvent.sequence > after_sequence)
            .order_by(TaskEvent.sequence.asc())
            .limit(min(limit, 500))
        )
    ).all()
    return [_to_wire(row) for row in rows]