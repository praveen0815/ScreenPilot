from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkflowRunWhen(StrEnum):
    ALWAYS = "always"
    ON_PREV_SUCCESS = "on_prev_success"
    ON_PREV_FAILURE = "on_prev_failure"


class StepOutcomeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int
    success: bool
    skipped: bool = False
    attempts: int = 0
    output_preview: str | None = None
    idempotency_key: str | None = None


class WorkflowState(BaseModel):
    """Persisted execution cursor and outcomes for crash-safe resume."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    last_sequence: int = 0
    last_success: bool | None = None
    execution_budget_used: int = 0
    outcomes: dict[str, StepOutcomeRecord] = Field(default_factory=dict)
    idempotency_completed: list[str] = Field(default_factory=list)
    revision_count: int = 0
    paused_at_sequence: int | None = None


class WorkflowRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed", "cancelled", "paused", "blocked"]
    message: str
    completed_steps: int = 0
    skipped_steps: int = 0