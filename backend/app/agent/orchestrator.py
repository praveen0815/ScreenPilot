import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import compile_agent_graph
from app.agent.llm.factory import get_llm_provider
from app.agent.state import AgentGraphState
from app.core.errors import AppError, NotFoundError
from app.db.enums import ApprovalStatus, TaskStatus
from app.db.models.agent_task import AgentTask
from app.db.models.user import User
from app.schemas.agent import AgentOutcome
from app.safety.approval_service import approve_request, expire_pending_approvals, list_pending_approvals
from app.services import agent_repository
from app.auth.permissions import ROLE_PERMISSIONS
from app.tools.executor_service import ToolExecutorService
from app.tools.registry import ToolRegistry, build_registry


def _coerce_status(value: TaskStatus | str) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    return TaskStatus(value)


def _coerce_approval_status(value: ApprovalStatus | str) -> ApprovalStatus:
    if isinstance(value, ApprovalStatus):
        return value
    return ApprovalStatus(value)


@dataclass
class OrchestratorContext:
    session: AsyncSession
    user: User
    task: AgentTask
    tool_executor: ToolExecutorService
    registry: ToolRegistry


class AgentOrchestrator:
    """Runs the LangGraph planning and mock execution loop with PostgreSQL persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.llm = get_llm_provider()

    async def run_task(self, user: User, task_id: uuid.UUID, *, resume: bool = False) -> AgentOutcome:
        task = await agent_repository.load_task(self.session, task_id, user.id)
        if task is None:
            raise NotFoundError("Task not found.")
        status = _coerce_status(task.status)

        if status is TaskStatus.AWAITING_APPROVAL and not resume:
            raise AppError(
                code="approval_required",
                message="Task is waiting for approval before execution can continue.",
                status_code=409,
            )
        if resume and status is TaskStatus.AWAITING_APPROVAL:
            await expire_pending_approvals(self.session, task)
            await self.session.refresh(task, attribute_names=["approval_requests"])
            if any(_coerce_approval_status(a.status) is ApprovalStatus.DENIED for a in task.approval_requests):
                raise AppError(
                    code="approval_rejected",
                    message="Plan was rejected and cannot be resumed.",
                    status_code=409,
                )
            if any(_coerce_approval_status(a.status) is ApprovalStatus.EXPIRED for a in task.approval_requests):
                raise AppError(
                    code="approval_expired",
                    message="Approval expired. Re-run the task to create a new approval request.",
                    status_code=409,
                )
            pending = await list_pending_approvals(self.session, task, user.id)
            if pending:
                raise AppError(
                    code="approval_required",
                    message="Approve the plan before resuming execution.",
                    status_code=409,
                )

        if status not in {TaskStatus.PENDING, TaskStatus.AWAITING_APPROVAL, TaskStatus.PAUSED}:
            if status is TaskStatus.RUNNING:
                raise AppError(
                    code="task_running",
                    message="Task is already running.",
                    status_code=409,
                )
            if status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
                raise AppError(
                    code="invalid_transition",
                    message=f"Task is already {status.value}.",
                    status_code=409,
                )

        ctx = OrchestratorContext(
            session=self.session,
            user=user,
            task=task,
            tool_executor=ToolExecutorService(),
            registry=build_registry(),
        )
        graph = compile_agent_graph(ctx, self.llm)

        initial: AgentGraphState = {
            "task_id": str(task.id),
            "instruction": task.instruction,
            "intent_json": task.intent_json,
            "plan_json": task.plan_json,
            "current_step_index": 0,
            "cancelled": task.cancel_requested,
            "paused": task.pause_requested,
            "resume_execution_only": resume and status is TaskStatus.AWAITING_APPROVAL,
        }

        final = await graph.ainvoke(initial)
        await self.session.refresh(task)
        return self._outcome_from_state(task, final)

    async def cancel_task(self, user: User, task_id: uuid.UUID) -> AgentTask:
        task = await agent_repository.load_task(self.session, task_id, user.id)
        if task is None:
            raise NotFoundError("Task not found.")
        status = _coerce_status(task.status)
        if status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            raise AppError(
                code="invalid_transition",
                message="Task is already finished.",
                status_code=409,
            )
        task.cancel_requested = True
        if status not in {TaskStatus.RUNNING, TaskStatus.PLANNING}:
            await agent_repository.set_status(
                self.session, task, TaskStatus.CANCELLED, message="Cancelled by user."
            )
        await self.session.flush()
        return task

    async def pause_task(self, user: User, task_id: uuid.UUID) -> AgentTask:
        task = await agent_repository.load_task(self.session, task_id, user.id)
        if task is None:
            raise NotFoundError("Task not found.")
        if _coerce_status(task.status) is not TaskStatus.RUNNING:
            raise AppError(
                code="invalid_transition",
                message="Only running tasks can be paused.",
                status_code=409,
            )
        task.pause_requested = True
        await agent_repository.set_status(self.session, task, TaskStatus.PAUSED, message="Paused by user.")
        return task

    async def approve_task(self, user: User, task_id: uuid.UUID) -> AgentTask:
        task = await agent_repository.load_task(self.session, task_id, user.id)
        if task is None:
            raise NotFoundError("Task not found.")
        if _coerce_status(task.status) is not TaskStatus.AWAITING_APPROVAL:
            raise AppError(
                code="invalid_transition",
                message="Task is not awaiting approval.",
                status_code=409,
            )
        pending = await list_pending_approvals(self.session, task, user.id)
        if not pending:
            raise AppError(
                code="approval_not_pending",
                message="No pending approval requests for this task.",
                status_code=409,
            )
        for row in pending:
            await approve_request(self.session, user, row.id)
        await self.session.refresh(task)
        return task

    async def reject_approval(
        self,
        user: User,
        task_id: uuid.UUID,
        approval_id: uuid.UUID,
        *,
        reason: str | None = None,
    ) -> AgentTask:
        from app.safety.approval_service import reject_request

        task = await agent_repository.load_task(self.session, task_id, user.id)
        if task is None:
            raise NotFoundError("Task not found.")
        if _coerce_status(task.status) is not TaskStatus.AWAITING_APPROVAL:
            raise AppError(
                code="invalid_transition",
                message="Task is not awaiting approval.",
                status_code=409,
            )
        await reject_request(self.session, user, approval_id, reason=reason)
        await agent_repository.set_status(self.session, task, TaskStatus.FAILED, message="Plan rejected.")
        await self.session.refresh(task)
        return task

    def _outcome_from_state(self, task: AgentTask, state: AgentGraphState) -> AgentOutcome:
        status = _coerce_status(task.status)
        if state.get("cancelled") or status is TaskStatus.CANCELLED:
            return AgentOutcome(status="cancelled", message=task.outcome_message or "Task cancelled.")
        if state.get("planning_failed") or status is TaskStatus.FAILED:
            return AgentOutcome(
                status="failed",
                message=task.outcome_message or state.get("failure_message") or "Task failed.",
            )
        if status is TaskStatus.AWAITING_APPROVAL:
            return AgentOutcome(status="needs_user", message="Plan requires user approval.")
        if status is TaskStatus.COMPLETED:
            return AgentOutcome(status="completed", message=task.outcome_message or "Task completed.")
        if status is TaskStatus.PAUSED:
            return AgentOutcome(status="needs_user", message="Task paused.")
        return AgentOutcome(status="failed", message="Task ended in an unexpected state.")