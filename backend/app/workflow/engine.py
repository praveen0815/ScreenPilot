import asyncio
import logging
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.schemas.plan import PlanStepSpec, TaskPlan
from app.core.config import get_settings
from app.db.enums import ExecutionStatus, StepStatus, TaskStatus, ToolExecutionStatus
from app.db.models.agent_execution import AgentExecution
from app.db.models.agent_task import AgentTask
from app.db.models.task_step import TaskStep
from app.db.models.user import User
from app.events.schemas import TaskEventType
from app.events.service import publish_task_event
from app.memory.service import MemoryService
from app.safety.risk import ActionRiskLevel, classify_tool
from app.safety.effective_permissions import effective_permissions
from app.services import agent_repository
from app.tools.contracts import ToolContext
from app.tools.errors import ToolPermissionError
from app.tools.executor_service import ToolExecutorService
from app.tools.registry import ToolRegistry
from app.workflow.completion import WorkflowCompletionError, validate_workflow_completion
from app.workflow.conditions import should_run_step
from app.workflow.dependencies import resolve_execution_order
from app.workflow.repository import load_workflow_state, persist_workflow_state
from app.workflow.schemas import StepOutcomeRecord, WorkflowRunResult, WorkflowState

logger = logging.getLogger("app.workflow.engine")


def _coerce_step_status(value: StepStatus | str) -> StepStatus:
    if isinstance(value, StepStatus):
        return value
    return StepStatus(value)


@dataclass
class WorkflowContext:
    session: AsyncSession
    user: User
    task: AgentTask
    tool_executor: ToolExecutorService
    registry: ToolRegistry


class WorkflowEngine:
    """Deterministic multi-step workflow runner with retries, checkpoints, and resume."""

    def __init__(self, ctx: WorkflowContext) -> None:
        self.ctx = ctx
        self.settings = get_settings()

    async def run(
        self,
        plan: TaskPlan,
        *,
        record: AgentExecution,
        resume_from_pause: bool = False,
    ) -> WorkflowRunResult:
        session = self.ctx.session
        task = self.ctx.task
        memory = MemoryService(session)
        state = load_workflow_state(task)

        if resume_from_pause and state.paused_at_sequence is not None:
            state.paused_at_sequence = None

        db_steps = sorted(
            (await session.scalars(select(TaskStep).where(TaskStep.task_id == task.id))).all(),
            key=lambda row: row.sequence,
        )
        by_seq = {row.sequence: row for row in db_steps}
        specs = resolve_execution_order(plan.steps)

        tool_context = ToolContext(
            task_id=task.id,
            user_id=self.ctx.user.id,
            permissions=effective_permissions(self.ctx.user),
            confirmed=True,
        )

        completed = 0
        skipped = 0

        for spec in specs:
            task = await agent_repository.refresh_cancel_pause(session, task)
            self.ctx.task = task

            if task.cancel_requested:
                await persist_workflow_state(session, task, state)
                await agent_repository.set_status(session, task, TaskStatus.CANCELLED, message="Cancelled during workflow.")
                await publish_task_event(
                    session,
                    user_id=self.ctx.user.id,
                    task_id=task.id,
                    event_type=TaskEventType.TASK_CANCELLED,
                    payload={"status": TaskStatus.CANCELLED.value, "message": "Cancelled during workflow."},
                    agent_execution_id=record.id,
                )
                await agent_repository.finish_execution_record(
                    session, record, status=ExecutionStatus.CANCELLED, message="Cancelled."
                )
                return WorkflowRunResult(status="cancelled", message="Cancelled.", completed_steps=completed, skipped_steps=skipped)

            if task.pause_requested:
                state.paused_at_sequence = spec.sequence
                await persist_workflow_state(session, task, state)
                await memory.save_checkpoint(
                    self.ctx.user,
                    task,
                    {"phase": "workflow_paused", "sequence": spec.sequence},
                )
                await agent_repository.set_status(session, task, TaskStatus.PAUSED, message="Workflow paused.")
                await publish_task_event(
                    session,
                    user_id=self.ctx.user.id,
                    task_id=task.id,
                    event_type=TaskEventType.TASK_PAUSED,
                    payload={
                        "status": TaskStatus.PAUSED.value,
                        "message": "Workflow paused.",
                        "step_sequence": spec.sequence,
                    },
                    agent_execution_id=record.id,
                )
                await agent_repository.finish_execution_record(
                    session, record, status=ExecutionStatus.CANCELLED, message="Paused."
                )
                return WorkflowRunResult(status="paused", message="Paused.", completed_steps=completed, skipped_steps=skipped)

            if state.execution_budget_used >= self.settings.workflow_max_executions_per_run:
                await agent_repository.set_status(
                    session, task, TaskStatus.FAILED, message="Workflow execution budget exceeded."
                )
                await publish_task_event(
                    session,
                    user_id=self.ctx.user.id,
                    task_id=task.id,
                    event_type=TaskEventType.TASK_FAILED,
                    payload={"status": TaskStatus.FAILED.value, "message": "Workflow execution budget exceeded."},
                    agent_execution_id=record.id,
                )
                await agent_repository.finish_execution_record(
                    session, record, status=ExecutionStatus.FAILED, message="Budget exceeded."
                )
                return WorkflowRunResult(status="failed", message="Execution budget exceeded.", completed_steps=completed, skipped_steps=skipped)

            step_row = by_seq.get(spec.sequence)
            if step_row is None:
                message = f"Missing step row for sequence {spec.sequence}."
                await agent_repository.set_status(session, task, TaskStatus.FAILED, message=message)
                return WorkflowRunResult(status="failed", message=message, completed_steps=completed, skipped_steps=skipped)

            if not self._dependencies_satisfied(spec, by_seq):
                continue

            if _coerce_step_status(step_row.status) is StepStatus.COMPLETED:
                outcome = state.outcomes.get(str(spec.sequence))
                state.last_success = outcome.success if outcome else True
                state.last_sequence = max(state.last_sequence, spec.sequence)
                completed += 1
                continue

            if not should_run_step(spec, state=state):
                await self._mark_skipped(session, task, step_row, spec, state)
                skipped += 1
                state.last_sequence = max(state.last_sequence, spec.sequence)
                await persist_workflow_state(session, task, state)
                continue

            if spec.idempotency_key and spec.idempotency_key in state.idempotency_completed:
                await self._mark_skipped(session, task, step_row, spec, state, reason="idempotent")
                skipped += 1
                state.last_sequence = max(state.last_sequence, spec.sequence)
                await persist_workflow_state(session, task, state)
                continue

            if self._is_sensitive_duplicate(spec, state):
                await agent_repository.set_status(
                    session, task, TaskStatus.FAILED, message=f"Duplicate sensitive step {spec.sequence} blocked."
                )
                return WorkflowRunResult(status="blocked", message="Duplicate sensitive action.", completed_steps=completed, skipped_steps=skipped)

            step_row.status = StepStatus.RUNNING
            await session.flush()
            await publish_task_event(
                session,
                user_id=self.ctx.user.id,
                task_id=task.id,
                event_type=TaskEventType.STEP_STARTED,
                payload={
                    "step_sequence": spec.sequence,
                    "tool_name": spec.tool_name,
                    "status": StepStatus.RUNNING.value,
                },
                agent_execution_id=record.id,
            )

            result = await self._execute_with_retry(spec, step_row, tool_context, state, record_id=record.id)
            state.execution_budget_used += result.attempts
            state.outcomes[str(spec.sequence)] = result
            state.last_sequence = spec.sequence
            state.last_success = result.success and not result.skipped

            if result.success and not result.skipped:
                completed += 1
                if spec.idempotency_key:
                    if spec.idempotency_key not in state.idempotency_completed:
                        state.idempotency_completed.append(spec.idempotency_key)
            elif result.skipped:
                skipped += 1
            else:
                if spec.skip_on_failure:
                    await self._mark_skipped(session, task, step_row, spec, state, reason="skip_on_failure")
                    skipped += 1
                    state.last_success = False
                    await persist_workflow_state(session, task, state)
                    await memory.save_checkpoint(
                        self.ctx.user,
                        task,
                        {"phase": "step_failed_continue", "sequence": spec.sequence},
                    )
                    continue
                await agent_repository.set_status(
                    session, task, TaskStatus.FAILED, message=f"Step {spec.sequence} failed after retries."
                )
                await publish_task_event(
                    session,
                    user_id=self.ctx.user.id,
                    task_id=task.id,
                    event_type=TaskEventType.TASK_FAILED,
                    payload={
                        "status": TaskStatus.FAILED.value,
                        "message": f"Step {spec.sequence} failed after retries.",
                        "step_sequence": spec.sequence,
                    },
                    agent_execution_id=record.id,
                )
                await agent_repository.finish_execution_record(
                    session, record, status=ExecutionStatus.FAILED, message=result.output_preview or "Failed."
                )
                await persist_workflow_state(session, task, state)
                return WorkflowRunResult(
                    status="failed",
                    message=result.output_preview or "Step failed.",
                    completed_steps=completed,
                    skipped_steps=skipped,
                )

            await persist_workflow_state(session, task, state)
            await memory.save_checkpoint(
                self.ctx.user,
                task,
                {"phase": "step_completed", "sequence": spec.sequence, "success": result.success},
            )

        db_steps = sorted(
            (await session.scalars(select(TaskStep).where(TaskStep.task_id == task.id))).all(),
            key=lambda row: row.sequence,
        )
        try:
            validate_workflow_completion(plan, steps=db_steps, state=state)
        except WorkflowCompletionError as exc:
            await agent_repository.set_status(session, task, TaskStatus.FAILED, message=exc.message)
            await publish_task_event(
                session,
                user_id=self.ctx.user.id,
                task_id=task.id,
                event_type=TaskEventType.TASK_FAILED,
                payload={"status": TaskStatus.FAILED.value, "message": exc.message[:500]},
                agent_execution_id=record.id,
            )
            await agent_repository.finish_execution_record(
                session, record, status=ExecutionStatus.FAILED, message=exc.message
            )
            return WorkflowRunResult(status="failed", message=exc.message, completed_steps=completed, skipped_steps=skipped)

        summary = self._build_summary(plan, state)
        await agent_repository.set_status(session, task, TaskStatus.COMPLETED, message=summary)
        await publish_task_event(
            session,
            user_id=self.ctx.user.id,
            task_id=task.id,
            event_type=TaskEventType.TASK_COMPLETED,
            payload={"status": TaskStatus.COMPLETED.value, "message": summary[:500]},
            agent_execution_id=record.id,
        )
        await agent_repository.finish_execution_record(
            session, record, status=ExecutionStatus.COMPLETED, message=summary
        )
        await memory.save_task_summary(self.ctx.user, task, summary)
        await persist_workflow_state(session, task, state)
        return WorkflowRunResult(status="completed", message=summary, completed_steps=completed, skipped_steps=skipped)

    def _dependencies_satisfied(self, spec: PlanStepSpec, rows: dict[int, TaskStep]) -> bool:
        for dep in spec.depends_on:
            row = rows.get(dep)
            if row is None:
                return False
            if _coerce_step_status(row.status) not in {StepStatus.COMPLETED, StepStatus.SKIPPED}:
                return False
        return True

    def _is_sensitive_duplicate(self, spec: PlanStepSpec, state: WorkflowState) -> bool:
        if not spec.idempotency_key:
            return False
        metadata = next(
            (item for item in self.ctx.registry.list_metadata() if item.name == spec.tool_name),
            None,
        )
        if metadata is None:
            return False
        if classify_tool(metadata) not in {ActionRiskLevel.HIGH, ActionRiskLevel.MODERATE}:
            return False
        key = f"{spec.idempotency_key}:{spec.tool_name}"
        return key in state.idempotency_completed

    async def _mark_skipped(
        self,
        session: AsyncSession,
        task: AgentTask,
        step_row: TaskStep,
        spec: PlanStepSpec,
        state: WorkflowState,
        *,
        reason: str = "conditional",
    ) -> None:
        step_row.status = StepStatus.SKIPPED
        await session.flush()
        state.outcomes[str(spec.sequence)] = StepOutcomeRecord(
            sequence=spec.sequence,
            success=False,
            skipped=True,
            attempts=0,
            output_preview=f"skipped:{reason}",
            idempotency_key=spec.idempotency_key,
        )
        await agent_repository.record_tool_run(
            session,
            task=task,
            step=step_row,
            tool_name=spec.tool_name,
            arguments=dict(spec.arguments),
            status=ToolExecutionStatus.FAILED,
            result=f"skipped:{reason}",
        )

    async def _execute_with_retry(
        self,
        spec: PlanStepSpec,
        step_row: TaskStep,
        tool_context: ToolContext,
        state: WorkflowState,
        *,
        record_id,
    ) -> StepOutcomeRecord:
        session = self.ctx.session
        task = self.ctx.task
        memory = MemoryService(session)
        max_attempts = min(
            spec.retry_max + 1,
            self.settings.workflow_max_retries_per_step + 1,
        )
        arguments = dict(spec.arguments)
        last_output: str | None = None

        for attempt in range(1, max_attempts + 1):
            arguments = dict(spec.arguments)
            if spec.retry_max > 0 or spec.tool_name == "mock.workflow.attempt":
                arguments["attempt"] = attempt
            timeout = spec.timeout_seconds or get_settings().tool_default_timeout_seconds
            try:
                result = await asyncio.wait_for(
                    self.ctx.tool_executor.execute(
                        spec.tool_name,
                        arguments,
                        tool_context,
                        self.ctx.registry,
                        session=session,
                        agent_execution_id=record_id,
                        step_sequence=spec.sequence,
                    ),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                last_output = f"Step timed out after {timeout}s."
                if attempt < max_attempts:
                    await asyncio.sleep(spec.retry_backoff_seconds)
                    continue
                break
            except ToolPermissionError as exc:
                last_output = str(exc)
                await agent_repository.record_tool_run(
                    session,
                    task=task,
                    step=step_row,
                    tool_name=spec.tool_name,
                    arguments=arguments,
                    status=ToolExecutionStatus.BLOCKED,
                    result=last_output,
                )
                return StepOutcomeRecord(
                    sequence=spec.sequence,
                    success=False,
                    attempts=attempt,
                    output_preview=last_output,
                    idempotency_key=spec.idempotency_key,
                )
            except Exception as exc:
                last_output = str(exc)
                if attempt < max_attempts:
                    await asyncio.sleep(spec.retry_backoff_seconds)
                    continue
                break

            blocked = result.error_code == ToolPermissionError.code
            if not result.success:
                last_output = result.output
                await agent_repository.record_tool_run(
                    session,
                    task=task,
                    step=step_row,
                    tool_name=spec.tool_name,
                    arguments=arguments,
                    status=ToolExecutionStatus.BLOCKED if blocked else ToolExecutionStatus.FAILED,
                    result=last_output,
                )
                if blocked or attempt >= max_attempts:
                    return StepOutcomeRecord(
                        sequence=spec.sequence,
                        success=False,
                        attempts=attempt,
                        output_preview=last_output,
                        idempotency_key=spec.idempotency_key,
                    )
                await asyncio.sleep(spec.retry_backoff_seconds)
                continue

            await agent_repository.record_tool_run(
                session,
                task=task,
                step=step_row,
                tool_name=spec.tool_name,
                arguments=arguments,
                status=ToolExecutionStatus.SUCCEEDED,
                result=result.output,
            )
            await memory.append_tool_result(
                self.ctx.user,
                task,
                tool_name=spec.tool_name,
                success=True,
                output=result.output,
                data=result.data,
            )
            return StepOutcomeRecord(
                sequence=spec.sequence,
                success=True,
                attempts=attempt,
                output_preview=(result.output or "")[:300],
                idempotency_key=spec.idempotency_key,
            )

        await agent_repository.record_tool_run(
            session,
            task=task,
            step=step_row,
            tool_name=spec.tool_name,
            arguments=arguments,
            status=ToolExecutionStatus.FAILED,
            result=last_output,
        )
        return StepOutcomeRecord(
            sequence=spec.sequence,
            success=False,
            attempts=max_attempts,
            output_preview=last_output,
            idempotency_key=spec.idempotency_key,
        )

    def _build_summary(self, plan: TaskPlan, state: WorkflowState) -> str:
        successes = sum(1 for item in state.outcomes.values() if item.success)
        skipped = sum(1 for item in state.outcomes.values() if item.skipped)
        return (
            f"Workflow completed for goal: {plan.goal[:120]}. "
            f"Steps succeeded={successes}, skipped={skipped}, budget_used={state.execution_budget_used}."
        )