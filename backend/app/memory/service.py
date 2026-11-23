import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.enums import MemoryEntryKind, MemoryScope
from app.db.models.agent_task import AgentTask
from app.db.models.task_memory_entry import TaskMemoryEntry
from app.db.models.user import User
from app.memory.errors import MemoryPolicyError
from app.memory.repository import (
    append_entry,
    clear_task_memory,
    count_task_entries,
    delete_expired_entries,
    delete_oldest_entries,
    load_task_entries,
    load_user_preferences,
    persist_checkpoint,
    persist_task_summary,
    save_user_preferences,
)
from app.memory.sanitize import sanitize_mapping_for_memory, sanitize_preferences, sanitize_text_for_memory
from app.memory.schemas import MemoryEntryView, PlanningContext, TaskMemoryBundle
from app.memory.window import assemble_planning_context

logger = logging.getLogger("app.memory.service")


class MemoryService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    def _expires_for(self, kind: MemoryEntryKind) -> datetime | None:
        now = datetime.now(timezone.utc)
        if kind in {MemoryEntryKind.SHORT_TERM, MemoryEntryKind.TOOL_RESULT}:
            return now + timedelta(hours=self.settings.memory_short_term_ttl_hours)
        if kind in {MemoryEntryKind.CONVERSATION_USER, MemoryEntryKind.CONVERSATION_ASSISTANT}:
            return now + timedelta(days=self.settings.memory_conversation_ttl_days)
        if kind is MemoryEntryKind.CHECKPOINT:
            return now + timedelta(days=self.settings.memory_checkpoint_ttl_days)
        if kind is MemoryEntryKind.TASK_SUMMARY:
            return now + timedelta(days=self.settings.memory_summary_ttl_days)
        return None

    async def cleanup_expired(self, user_id: UUID) -> int:
        if not self.settings.memory_retention_cleanup_enabled:
            return 0
        removed = await delete_expired_entries(self.session, user_id=user_id)
        if removed:
            logger.info("memory_expired_cleanup", extra={"user_id": str(user_id), "removed": removed})
        return removed

    async def _enforce_limits(self, user_id: UUID, task_id: UUID) -> None:
        total = await count_task_entries(self.session, user_id=user_id, task_id=task_id)
        max_entries = self.settings.memory_max_entries_per_task
        if total >= max_entries:
            await delete_oldest_entries(
                self.session,
                user_id=user_id,
                task_id=task_id,
                remove_count=total - max_entries + 1,
            )

    async def _add(
        self,
        *,
        user: User,
        task: AgentTask,
        scope: MemoryScope,
        kind: MemoryEntryKind,
        content: str,
    ) -> TaskMemoryEntry | None:
        if task.user_id != user.id:
            raise MemoryPolicyError("Task is not owned by this user.")
        try:
            safe = sanitize_text_for_memory(content, max_chars=self.settings.memory_max_chars_per_entry)
        except MemoryPolicyError:
            logger.warning(
                "memory_entry_rejected",
                extra={"user_id": str(user.id), "task_id": str(task.id), "kind": kind.value},
            )
            return None
        await self._enforce_limits(user.id, task.id)
        return await append_entry(
            self.session,
            user_id=user.id,
            task_id=task.id,
            scope=scope,
            kind=kind,
            content=safe,
            expires_at=self._expires_for(kind),
        )

    async def append_conversation_user(self, user: User, task: AgentTask, content: str) -> None:
        await self._add(
            user=user,
            task=task,
            scope=MemoryScope.CONVERSATION,
            kind=MemoryEntryKind.CONVERSATION_USER,
            content=content,
        )

    async def append_conversation_assistant(self, user: User, task: AgentTask, content: str) -> None:
        await self._add(
            user=user,
            task=task,
            scope=MemoryScope.CONVERSATION,
            kind=MemoryEntryKind.CONVERSATION_ASSISTANT,
            content=content,
        )

    async def append_tool_result(
        self,
        user: User,
        task: AgentTask,
        *,
        tool_name: str,
        success: bool,
        output: str | None,
        data: dict | None,
    ) -> None:
        summary = {
            "tool_name": tool_name,
            "success": success,
            "output": (output or "")[:500],
        }
        if data is not None:
            try:
                summary["data"] = json.loads(
                    sanitize_mapping_for_memory(data, max_chars=self.settings.memory_max_chars_per_entry)
                )
            except MemoryPolicyError:
                summary["data"] = {"redacted": True}
            except json.JSONDecodeError:
                summary["data"] = {"truncated": True}
        await self._add(
            user=user,
            task=task,
            scope=MemoryScope.TASK,
            kind=MemoryEntryKind.TOOL_RESULT,
            content=json.dumps(summary),
        )

    async def save_checkpoint(self, user: User, task: AgentTask, payload: dict) -> None:
        safe = sanitize_mapping_for_memory(payload, max_chars=self.settings.memory_max_chars_per_entry)
        await self._add(
            user=user,
            task=task,
            scope=MemoryScope.TASK,
            kind=MemoryEntryKind.CHECKPOINT,
            content=safe,
        )
        await persist_checkpoint(self.session, task, json.loads(safe))

    async def save_task_summary(self, user: User, task: AgentTask, summary: str) -> None:
        safe = sanitize_text_for_memory(summary, max_chars=self.settings.memory_max_chars_per_entry)
        await self._add(
            user=user,
            task=task,
            scope=MemoryScope.TASK,
            kind=MemoryEntryKind.TASK_SUMMARY,
            content=safe,
        )
        await persist_task_summary(self.session, task, safe)

    def _to_view(self, row: TaskMemoryEntry) -> MemoryEntryView:
        return MemoryEntryView(
            id=row.id,
            scope=row.scope if isinstance(row.scope, MemoryScope) else MemoryScope(row.scope),
            kind=row.kind if isinstance(row.kind, MemoryEntryKind) else MemoryEntryKind(row.kind),
            content=row.content,
            content_chars=row.content_chars,
            expires_at=row.expires_at,
            created_at=row.created_at,
        )

    async def get_task_memory(self, user: User, task: AgentTask) -> TaskMemoryBundle:
        if task.user_id != user.id:
            raise MemoryPolicyError("Task is not owned by this user.")
        rows = await load_task_entries(self.session, user_id=user.id, task_id=task.id)
        conversation = [
            self._to_view(row)
            for row in rows
            if (row.kind if isinstance(row.kind, MemoryEntryKind) else MemoryEntryKind(row.kind))
            in {MemoryEntryKind.CONVERSATION_USER, MemoryEntryKind.CONVERSATION_ASSISTANT}
        ]
        tools = [
            self._to_view(row)
            for row in rows
            if (row.kind if isinstance(row.kind, MemoryEntryKind) else MemoryEntryKind(row.kind))
            is MemoryEntryKind.TOOL_RESULT
        ]
        task_ctx = [
            self._to_view(row)
            for row in rows
            if (row.kind if isinstance(row.kind, MemoryEntryKind) else MemoryEntryKind(row.kind))
            in {MemoryEntryKind.SHORT_TERM, MemoryEntryKind.CHECKPOINT}
        ]
        checkpoint = None
        if task.context_checkpoint_json:
            try:
                checkpoint = json.loads(task.context_checkpoint_json)
            except json.JSONDecodeError:
                checkpoint = None
        total_chars = sum(row.content_chars for row in rows)
        return TaskMemoryBundle(
            task_id=task.id,
            task_summary=task.task_summary,
            checkpoint=checkpoint,
            conversation=conversation,
            task_context=task_ctx,
            recent_tool_results=tools[-self.settings.memory_recent_tool_results_limit :],
            total_entries=len(rows),
            context_window_chars=total_chars,
            truncated=total_chars > self.settings.memory_context_window_chars,
        )

    async def build_planning_context(self, user: User, task: AgentTask) -> tuple[PlanningContext, bool]:
        prefs = await load_user_preferences(self.session, user.id)
        rows = await load_task_entries(self.session, user_id=user.id, task_id=task.id)
        conversation_lines = [
            f"{row.kind}: {row.content[:300]}"
            for row in rows
            if str(row.kind).startswith("conversation_")
        ]
        tool_lines = [
            row.content[:400]
            for row in rows
            if (row.kind if isinstance(row.kind, MemoryEntryKind) else MemoryEntryKind(row.kind))
            is MemoryEntryKind.TOOL_RESULT
        ][-self.settings.memory_recent_tool_results_limit :]
        checkpoint_note = None
        if task.context_checkpoint_json:
            checkpoint_note = task.context_checkpoint_json[:500]
        return assemble_planning_context(
            instruction=task.instruction,
            task_summary=task.task_summary,
            conversation_lines=conversation_lines,
            tool_result_lines=tool_lines,
            user_preferences=prefs,
            checkpoint_note=checkpoint_note,
            max_chars=self.settings.memory_context_window_chars,
        )

    async def clear_task_memory(self, user: User, task: AgentTask) -> int:
        if task.user_id != user.id:
            raise MemoryPolicyError("Task is not owned by this user.")
        removed = await clear_task_memory(self.session, user_id=user.id, task_id=task.id)
        task.task_summary = None
        task.context_checkpoint_json = None
        await self.session.flush()
        return removed

    async def get_preferences(self, user: User) -> dict[str, str]:
        return await load_user_preferences(self.session, user.id)

    async def update_preferences(self, user: User, updates: dict[str, str]) -> dict[str, str]:
        current = await load_user_preferences(self.session, user.id)
        cleaned = sanitize_preferences({**current, **updates})
        return await save_user_preferences(self.session, user.id, cleaned)