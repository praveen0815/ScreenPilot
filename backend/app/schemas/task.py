from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import (
    ApprovalStatus,
    ExecutionStatus,
    StepStatus,
    TaskStatus,
    ToolExecutionStatus,
)


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str = Field(min_length=1, max_length=4000)


class AgentTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    instruction: str
    status: TaskStatus
    outcome_message: str | None = None
    cancel_requested: bool = False
    pause_requested: bool = False
    created_at: datetime
    updated_at: datetime


class TaskStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence: int
    description: str
    tool_name: str | None = None
    status: StepStatus
    created_at: datetime
    updated_at: datetime


class AgentExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ExecutionStatus
    outcome_message: str | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class ToolExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tool_name: str
    status: ToolExecutionStatus
    arguments_json: str | None
    result_json: str | None
    created_at: datetime


class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    status: ApprovalStatus
    detail: str | None
    display_json: str | None = None
    expires_at: datetime | None = None
    decided_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentTaskDetailResponse(AgentTaskResponse):
    steps: list[TaskStepResponse] = Field(default_factory=list)
    agent_executions: list[AgentExecutionResponse] = Field(default_factory=list)
    tool_executions: list[ToolExecutionResponse] = Field(default_factory=list)
    approval_requests: list[ApprovalRequestResponse] = Field(default_factory=list)