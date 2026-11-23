from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import MemoryEntryKind, MemoryScope


class PlanningContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_instruction: str
    task_summary: str | None = None
    conversation_turns: list[str] = Field(default_factory=list)
    recent_tool_results: list[str] = Field(default_factory=list)
    user_preferences: dict[str, str] = Field(default_factory=dict)
    checkpoint_note: str | None = None


class MemoryEntryView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    scope: MemoryScope
    kind: MemoryEntryKind
    content: str
    content_chars: int
    expires_at: datetime | None
    created_at: datetime


class TaskMemoryBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    task_summary: str | None
    checkpoint: dict | None
    conversation: list[MemoryEntryView] = Field(default_factory=list)
    task_context: list[MemoryEntryView] = Field(default_factory=list)
    recent_tool_results: list[MemoryEntryView] = Field(default_factory=list)
    total_entries: int
    context_window_chars: int
    truncated: bool = False