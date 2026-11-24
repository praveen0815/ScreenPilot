from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskEventType(StrEnum):
    TASK_CREATED = "task_created"
    PLANNING_STARTED = "planning_started"
    PLAN_GENERATED = "plan_generated"
    STEP_STARTED = "step_started"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    APPROVAL_REQUIRED = "approval_required"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    TASK_CANCELLED = "task_cancelled"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


PERSISTED_EVENT_TYPES = frozenset(TaskEventType)


class TaskEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str | None = None
    status: str | None = None
    step_sequence: int | None = Field(default=None, ge=1, le=50)
    tool_name: str | None = Field(default=None, max_length=120)
    outcome_status: str | None = Field(default=None, max_length=40)
    approval_id: str | None = None


class TaskEventWire(BaseModel):
    """Validated wire format for WebSocket and REST."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    task_id: UUID
    user_id: UUID
    type: TaskEventType
    sequence: int = Field(ge=1)
    occurred_at: datetime
    agent_execution_id: UUID | None = None
    tool_execution_id: UUID | None = None
    payload: TaskEventPayload = Field(default_factory=TaskEventPayload)


class WsClientMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(pattern=r"^(ping|resume|subscribe)$")
    task_id: UUID | None = None
    last_sequence: int | None = Field(default=None, ge=0)


class WsServerMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    event: TaskEventWire | None = None
    message: str | None = None


def sanitize_payload(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {}
    cleaned: dict[str, Any] = {}
    secret_markers = ("password", "token", "secret", "credential", "api_key", "bearer")
    for key, value in raw.items():
        key_l = str(key).lower()
        if any(marker in key_l for marker in secret_markers):
            cleaned[str(key)] = "[redacted]"
            continue
        if isinstance(value, str):
            if any(marker in value.lower() for marker in secret_markers):
                cleaned[str(key)] = "[redacted]"
            else:
                cleaned[str(key)] = value[:500]
        elif isinstance(value, (int, float, bool)) or value is None:
            cleaned[str(key)] = value
        else:
            cleaned[str(key)] = str(value)[:500]
    return cleaned