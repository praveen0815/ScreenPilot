from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.task import ApprovalRequestResponse


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=500)


class PendingApprovalsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    approvals: list[ApprovalRequestResponse]