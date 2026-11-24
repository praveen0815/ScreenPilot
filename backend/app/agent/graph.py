import json
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agent.llm.protocol import LLMProvider
from app.agent.plan_validator import PlanValidationError, validate_plan
from app.agent.planner import build_plan, interpret_intent
from app.agent.schemas.plan import TaskIntent, TaskPlan
from app.agent.state import AgentGraphState
from app.core.errors import AppError
from app.db.enums import ApprovalStatus, TaskStatus
from app.db.models.approval_request import ApprovalRequest
from sqlalchemy import select

from app.events.schemas import TaskEventType
from app.events.service import publish_task_event
from app.memory.service import MemoryService
from app.safety.approval_service import (
    create_task_approvals,
    expire_pending_approvals,
    plan_requires_approval,
)
from app.services import agent_repository
from app.workflow.engine import WorkflowContext, WorkflowEngine


def _coerce_status(value: TaskStatus | str) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    return TaskStatus(value)


def compile_agent_graph(ctx, llm: LLMProvider):
    graph: StateGraph = StateGraph(AgentGraphState)

    async def check_cancel(state: AgentGraphState) -> AgentGraphState:
        task = await agent_repository.refresh_cancel_pause(ctx.session, ctx.task)
        ctx.task = task
        if task.cancel_requested:
            await agent_repository.set_status(
                ctx.session, task, TaskStatus.CANCELLED, message="Cancelled by user."
            )
            await publish_task_event(
                ctx.session,
                user_id=ctx.user.id,
                task_id=task.id,
                event_type=TaskEventType.TASK_CANCELLED,
                payload={"status": TaskStatus.CANCELLED.value, "message": "Cancelled by user."},
            )
            return {**state, "cancelled": True, "done": True}
        return state

    async def interpret(state: AgentGraphState) -> AgentGraphState:
        task = ctx.task
        memory = MemoryService(ctx.session)
        await memory.cleanup_expired(ctx.user.id)
        planning_ctx, _ = await memory.build_planning_context(ctx.user, task)
        await agent_repository.set_status(ctx.session, task, TaskStatus.PLANNING)
        await publish_task_event(
            ctx.session,
            user_id=ctx.user.id,
            task_id=task.id,
            event_type=TaskEventType.PLANNING_STARTED,
            payload={"status": TaskStatus.PLANNING.value},
        )
        try:
            await memory.append_conversation_user(ctx.user, task, task.instruction)
            intent = await interpret_intent(llm, task.instruction, context=planning_ctx)
        except Exception as exc:
            await agent_repository.set_status(
                ctx.session,
                task,
                TaskStatus.FAILED,
                message="Intent interpretation failed.",
            )
            await publish_task_event(
                ctx.session,
                user_id=ctx.user.id,
                task_id=task.id,
                event_type=TaskEventType.TASK_FAILED,
                payload={"status": TaskStatus.FAILED.value, "message": "Intent interpretation failed."},
            )
            return {**state, "planning_failed": True, "failure_message": str(exc), "done": True}
        intent_json = intent.model_dump_json()
        await agent_repository.persist_intent(ctx.session, task, intent_json)
        await memory.append_conversation_assistant(ctx.user, task, intent.summary)
        return {**state, "intent_json": intent_json}

    async def plan(state: AgentGraphState) -> AgentGraphState:
        task = ctx.task
        memory = MemoryService(ctx.session)
        intent = TaskIntent.model_validate_json(state["intent_json"] or task.intent_json or "{}")
        planning_ctx, _ = await memory.build_planning_context(ctx.user, task)
        try:
            built = await build_plan(llm, task.instruction, intent, context=planning_ctx)
        except AppError as exc:
            await agent_repository.set_status(ctx.session, task, TaskStatus.FAILED, message=exc.message)
            await publish_task_event(
                ctx.session,
                user_id=ctx.user.id,
                task_id=task.id,
                event_type=TaskEventType.TASK_FAILED,
                payload={"status": TaskStatus.FAILED.value, "message": exc.message},
            )
            return {**state, "planning_failed": True, "failure_message": exc.message, "done": True}
        except Exception as exc:
            await agent_repository.set_status(
                ctx.session, task, TaskStatus.FAILED, message="Planning failed."
            )
            await publish_task_event(
                ctx.session,
                user_id=ctx.user.id,
                task_id=task.id,
                event_type=TaskEventType.TASK_FAILED,
                payload={"status": TaskStatus.FAILED.value, "message": "Planning failed."},
            )
            return {**state, "planning_failed": True, "failure_message": str(exc), "done": True}
        return {**state, "plan_json": built.model_dump_json()}

    async def validate(state: AgentGraphState) -> AgentGraphState:
        if state.get("done"):
            return state
        task = ctx.task
        raw = state.get("plan_json")
        if not raw:
            await agent_repository.set_status(
                ctx.session, task, TaskStatus.FAILED, message="Missing plan."
            )
            await publish_task_event(
                ctx.session,
                user_id=ctx.user.id,
                task_id=task.id,
                event_type=TaskEventType.TASK_FAILED,
                payload={"status": TaskStatus.FAILED.value, "message": "Missing plan."},
            )
            return {**state, "planning_failed": True, "failure_message": "Missing plan.", "done": True}
        plan = TaskPlan.model_validate_json(raw)
        try:
            validate_plan(plan)
        except PlanValidationError as exc:
            await agent_repository.set_status(
                ctx.session, task, TaskStatus.FAILED, message=exc.message
            )
            await publish_task_event(
                ctx.session,
                user_id=ctx.user.id,
                task_id=task.id,
                event_type=TaskEventType.TASK_FAILED,
                payload={"status": TaskStatus.FAILED.value, "message": exc.message},
            )
            return {
                **state,
                "validation_error": exc.message,
                "planning_failed": True,
                "failure_message": exc.message,
                "done": True,
            }
        needs_approval = plan_requires_approval(plan)
        return {**state, "needs_approval": needs_approval}

    async def persist_plan(state: AgentGraphState) -> AgentGraphState:
        task = ctx.task
        memory = MemoryService(ctx.session)
        plan = TaskPlan.model_validate_json(state["plan_json"])
        await agent_repository.persist_plan(ctx.session, task, plan)
        await memory.save_checkpoint(
            ctx.user,
            task,
            {"phase": "plan_persisted", "step_count": len(plan.steps), "goal": plan.goal[:200]},
        )
        await create_task_approvals(ctx.session, task=task, user=ctx.user, plan=plan)
        await ctx.session.refresh(task, attribute_names=["approval_requests"])
        await publish_task_event(
            ctx.session,
            user_id=ctx.user.id,
            task_id=task.id,
            event_type=TaskEventType.PLAN_GENERATED,
            payload={
                "message": f"Plan with {len(plan.steps)} steps.",
                "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            },
        )
        return state

    async def approval_gate(state: AgentGraphState) -> AgentGraphState:
        task = ctx.task
        if not state.get("needs_approval"):
            return state
        await expire_pending_approvals(ctx.session, task)
        approvals = (
            await ctx.session.scalars(select(ApprovalRequest).where(ApprovalRequest.task_id == task.id))
        ).all()

        def _status(row: ApprovalRequest) -> ApprovalStatus:
            return row.status if isinstance(row.status, ApprovalStatus) else ApprovalStatus(row.status)

        if any(_status(row) is ApprovalStatus.DENIED for row in approvals):
            await agent_repository.set_status(
                ctx.session,
                task,
                TaskStatus.FAILED,
                message="Plan was rejected.",
            )
            return {**state, "planning_failed": True, "failure_message": "Plan rejected.", "done": True}

        if any(_status(row) is ApprovalStatus.EXPIRED for row in approvals) and not state.get(
            "resume_execution_only"
        ):
            await agent_repository.set_status(
                ctx.session,
                task,
                TaskStatus.FAILED,
                message="Approval request expired.",
            )
            return {
                **state,
                "planning_failed": True,
                "failure_message": "Approval expired.",
                "done": True,
            }

        pending = any(_status(row) is ApprovalStatus.PENDING for row in approvals)
        if pending and not state.get("resume_execution_only"):
            await agent_repository.set_status(
                ctx.session,
                task,
                TaskStatus.AWAITING_APPROVAL,
                message="Plan requires human approval before execution.",
            )
            approval_id = str(approvals[0].id) if approvals else None
            await publish_task_event(
                ctx.session,
                user_id=ctx.user.id,
                task_id=task.id,
                event_type=TaskEventType.APPROVAL_REQUIRED,
                payload={
                    "status": TaskStatus.AWAITING_APPROVAL.value,
                    "message": "Plan requires human approval before execution.",
                    "approval_id": approval_id,
                },
            )
            return {**state, "done": True}

        if state.get("resume_execution_only"):
            approved = any(_status(row) is ApprovalStatus.APPROVED for row in approvals)
            if not approved:
                await agent_repository.set_status(
                    ctx.session,
                    task,
                    TaskStatus.FAILED,
                    message="Execution requires an approved plan.",
                )
                return {**state, "planning_failed": True, "failure_message": "Not approved.", "done": True}
        return state

    async def execute(state: AgentGraphState) -> AgentGraphState:
        task = ctx.task
        await agent_repository.set_status(ctx.session, task, TaskStatus.RUNNING)
        memory = MemoryService(ctx.session)
        record = await agent_repository.start_execution_record(ctx.session, task)
        plan = TaskPlan.model_validate_json(state["plan_json"] or task.plan_json)
        await memory.save_checkpoint(
            ctx.user,
            task,
            {"phase": "execution_started", "step_count": len(plan.steps)},
        )
        engine = WorkflowEngine(
            WorkflowContext(
                session=ctx.session,
                user=ctx.user,
                task=task,
                tool_executor=ctx.tool_executor,
                registry=ctx.registry,
            )
        )
        result = await engine.run(
            plan,
            record=record,
            resume_from_pause=bool(state.get("resume_from_pause")),
        )
        if result.status == "cancelled":
            return {**state, "cancelled": True, "done": True}
        if result.status == "paused":
            return {**state, "paused": True, "done": True}
        if result.status in {"failed", "blocked"}:
            return {
                **state,
                "planning_failed": True,
                "failure_message": result.message,
                "done": True,
            }
        return {**state, "done": True}

    def route_after_cancel(state: AgentGraphState) -> Literal["halt", "interpret", "execute"]:
        if state.get("done"):
            return "halt"
        if state.get("resume_execution_only"):
            return "execute"
        return "interpret"

    def route_after_validate(state: AgentGraphState) -> Literal["halt", "persist"]:
        return "halt" if state.get("done") else "persist"

    def route_after_approval(state: AgentGraphState) -> Literal["halt", "execute"]:
        return "halt" if state.get("done") else "execute"

    graph.add_node("check_cancel", check_cancel)
    graph.add_node("interpret", interpret)
    graph.add_node("plan", plan)
    graph.add_node("validate", validate)
    graph.add_node("persist_plan", persist_plan)
    graph.add_node("approval_gate", approval_gate)
    graph.add_node("execute", execute)

    graph.add_edge(START, "check_cancel")
    graph.add_conditional_edges(
        "check_cancel",
        route_after_cancel,
        {"halt": END, "interpret": "interpret", "execute": "execute"},
    )
    graph.add_edge("interpret", "plan")
    graph.add_edge("plan", "validate")
    graph.add_conditional_edges(
        "validate", route_after_validate, {"halt": END, "persist": "persist_plan"}
    )
    graph.add_edge("persist_plan", "approval_gate")
    graph.add_conditional_edges(
        "approval_gate", route_after_approval, {"halt": END, "execute": "execute"}
    )
    graph.add_edge("execute", END)

    return graph.compile()