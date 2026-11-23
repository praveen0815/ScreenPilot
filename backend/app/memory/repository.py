import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import MemoryEntryKind, MemoryScope
from app.db.models.agent_task import AgentTask
from app.db.models.task_memory_entry import TaskMemoryEntry
from app.db.models.user_agent_preference import UserAgentPreference


async def load_task_entries(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
) -> list[TaskMemoryEntry]:
    statement = (
        select(TaskMemoryEntry)
        .where(TaskMemoryEntry.user_id == user_id, TaskMemoryEntry.task_id == task_id)
        .order_by(TaskMemoryEntry.created_at.asc())
    )
    return list((await session.scalars(statement)).all())


async def append_entry(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    scope: MemoryScope,
    kind: MemoryEntryKind,
    content: str,
    expires_at: datetime | None,
) -> TaskMemoryEntry:
    row = TaskMemoryEntry(
        user_id=user_id,
        task_id=task_id,
        scope=scope,
        kind=kind,
        content=content,
        content_chars=len(content),
        expires_at=expires_at,
    )
    session.add(row)
    await session.flush()
    return row


async def count_task_entries(session: AsyncSession, *, user_id: uuid.UUID, task_id: uuid.UUID) -> int:
    statement = (
        select(func.count())
        .select_from(TaskMemoryEntry)
        .where(TaskMemoryEntry.user_id == user_id, TaskMemoryEntry.task_id == task_id)
    )
    return int(await session.scalar(statement) or 0)


async def delete_oldest_entries(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    remove_count: int,
) -> None:
    if remove_count <= 0:
        return
    statement = (
        select(TaskMemoryEntry.id)
        .where(TaskMemoryEntry.user_id == user_id, TaskMemoryEntry.task_id == task_id)
        .order_by(TaskMemoryEntry.created_at.asc())
        .limit(remove_count)
    )
    ids = list((await session.scalars(statement)).all())
    if ids:
        await session.execute(delete(TaskMemoryEntry).where(TaskMemoryEntry.id.in_(ids)))


async def clear_task_memory(session: AsyncSession, *, user_id: uuid.UUID, task_id: uuid.UUID) -> int:
    statement = delete(TaskMemoryEntry).where(
        TaskMemoryEntry.user_id == user_id,
        TaskMemoryEntry.task_id == task_id,
    )
    result = await session.execute(statement)
    await session.flush()
    return int(result.rowcount or 0)


async def delete_expired_entries(session: AsyncSession, *, user_id: uuid.UUID) -> int:
    now = datetime.now(timezone.utc)
    statement = delete(TaskMemoryEntry).where(
        TaskMemoryEntry.user_id == user_id,
        TaskMemoryEntry.expires_at.is_not(None),
        TaskMemoryEntry.expires_at < now,
    )
    result = await session.execute(statement)
    await session.flush()
    return int(result.rowcount or 0)


async def load_user_preferences(session: AsyncSession, user_id: uuid.UUID) -> dict[str, str]:
    row = await session.get(UserAgentPreference, user_id)
    if row is None:
        return {}
    try:
        data = json.loads(row.preferences_json or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(k, str)}


async def save_user_preferences(session: AsyncSession, user_id: uuid.UUID, prefs: dict[str, str]) -> dict[str, str]:
    row = await session.get(UserAgentPreference, user_id)
    payload = json.dumps(prefs)
    if row is None:
        row = UserAgentPreference(user_id=user_id, preferences_json=payload)
        session.add(row)
    else:
        row.preferences_json = payload
    await session.flush()
    return prefs


async def persist_checkpoint(session: AsyncSession, task: AgentTask, payload: dict) -> None:
    task.context_checkpoint_json = json.dumps(payload)
    await session.flush()


async def persist_task_summary(session: AsyncSession, task: AgentTask, summary: str) -> None:
    task.task_summary = summary
    await session.flush()