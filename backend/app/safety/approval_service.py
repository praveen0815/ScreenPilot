import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.schemas.plan import TaskPlan
from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.db.enums import ApprovalStatus
from app.db.models.agent_task import AgentTask
from app.db.models.approval_request import ApprovalRequest
from app.db.models.user import User
from app.safety.audit import log_approval_decision
from app.safety.confirmation import requires_confirmation
from app.safety.risk import SENSITIVE_PLAN_CATEGORIES, classify_tool
from app.tools.contracts import ToolRisk
from app.tools.registry import build_registry


def plan_requires_approval(plan: TaskPlan) -> bool:
    registry = build_registry()
    for step in plan.steps:
        metadata = next((item for item in registry.list_metadata() if item.name == step.tool_name), None)
        if metadata is None:
            continue
        level = classify_tool(metadata)
        if level.value in {"high", "moderate"} or step.risk is ToolRisk.HIGH:
            return True
    return False


def _display_payload(plan: TaskPlan) -> dict:
    registry = build_registry()
    steps = []
    for step in plan.steps:
        metadata = next((item for item in registry.list_metadata() if item.name == step.tool_name), None)
        risk = classify_tool(metadata).value if metadata else step.risk.value
        steps.append(
            {
                "sequence": step.sequence,
                "description": step.description,
                "tool_name": step.tool_name,
                "risk": risk,
                "requires_approval": requires_confirmation(step.risk) or risk in {"high", "moderate"},
            }
        )
    return {"goal": plan.goal, "steps": steps, "categories": list(SENSITIVE_PLAN_CATEGORIES)}


async def create_task_approvals(
    session: AsyncSession,
    *,
    task: AgentTask,
    user: User,
    plan: TaskPlan,
) -> list[ApprovalRequest]:
    settings = get_settings()
    registry = build_registry()
    if not plan_requires_approval(plan):
        return []

    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.approval_expire_hours)
    display = json.dumps(_display_payload(plan))
    approval = ApprovalRequest(
        task_id=task.id,
        user_id=user.id,
        category="high_risk_plan",
        detail="Plan includes actions that require human approval.",
        status=ApprovalStatus.PENDING,
        expires_at=expires_at,
        display_json=display,
    )
    session.add(approval)
    await session.flush()
    return [approval]


def _utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def expire_pending_approvals(session: AsyncSession, task: AgentTask) -> int:
    now = datetime.now(timezone.utc)
    count = 0
    for approval in task.approval_requests:
        status = approval.status if isinstance(approval.status, ApprovalStatus) else ApprovalStatus(approval.status)
        if status is not ApprovalStatus.PENDING:
            continue
        if approval.expires_at and _utc_aware(approval.expires_at) < now:
            approval.status = ApprovalStatus.EXPIRED
            count += 1
    if count:
        await session.flush()
    return count


async def list_pending_approvals(session: AsyncSession, task: AgentTask, user_id: UUID) -> list[ApprovalRequest]:
    await expire_pending_approvals(session, task)
    rows = (
        await session.scalars(
            select(ApprovalRequest).where(
                ApprovalRequest.task_id == task.id,
                ApprovalRequest.user_id == user_id,
            )
        )
    ).all()
    pending: list[ApprovalRequest] = []
    for row in rows:
        status = row.status if isinstance(row.status, ApprovalStatus) else ApprovalStatus(row.status)
        if status is ApprovalStatus.PENDING:
            pending.append(row)
    return pending


async def approve_request(session: AsyncSession, user: User, approval_id: UUID) -> ApprovalRequest:
    row = await session.get(ApprovalRequest, approval_id)
    if row is None or row.user_id != user.id:
        raise NotFoundError("Approval request not found.")
    task = await session.get(AgentTask, row.task_id)
    if task is not None:
        await session.refresh(task, attribute_names=["approval_requests"])
        await expire_pending_approvals(session, task)
    status = row.status if isinstance(row.status, ApprovalStatus) else ApprovalStatus(row.status)
    if status is ApprovalStatus.EXPIRED:
        raise AppError(code="approval_expired", message="Approval request expired.", status_code=409)
    if status is not ApprovalStatus.PENDING:
        raise AppError(code="approval_not_pending", message="Approval request is not pending.", status_code=409)
    row.status = ApprovalStatus.APPROVED
    row.decided_at = datetime.now(timezone.utc)
    await session.flush()
    await log_approval_decision(session, user_id=user.id, task_id=row.task_id, approval_id=row.id, decision="approved")
    return row


async def reject_request(
    session: AsyncSession,
    user: User,
    approval_id: UUID,
    *,
    reason: str | None = None,
) -> ApprovalRequest:
    row = await session.get(ApprovalRequest, approval_id)
    if row is None or row.user_id != user.id:
        raise NotFoundError("Approval request not found.")
    status = row.status if isinstance(row.status, ApprovalStatus) else ApprovalStatus(row.status)
    if status is not ApprovalStatus.PENDING:
        raise AppError(code="approval_not_pending", message="Approval request is not pending.", status_code=409)
    row.status = ApprovalStatus.DENIED
    row.decided_at = datetime.now(timezone.utc)
    row.rejection_reason = (reason or "Rejected by user.")[:500]
    await session.flush()
    await log_approval_decision(session, user_id=user.id, task_id=row.task_id, approval_id=row.id, decision="rejected")
    return row