from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import TaskStatus


class CreateAgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str = Field(min_length=1, max_length=4000)


class AgentTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    instruction: str = Field(min_length=1, max_length=4000)


class AgentOutcome(BaseModel):
    status: Literal["completed", "failed", "cancelled", "needs_user", "unavailable"]
    message: str


class RunTaskResponse(BaseModel):
    task_id: UUID
    status: TaskStatus
    outcome: AgentOutcome