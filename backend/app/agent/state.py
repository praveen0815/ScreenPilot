from typing import TypedDict


class AgentGraphState(TypedDict, total=False):
    task_id: str
    instruction: str
    intent_json: str | None
    plan_json: str | None
    validation_error: str | None
    needs_approval: bool
    current_step_index: int
    cancelled: bool
    paused: bool
    planning_failed: bool
    failure_message: str | None
    done: bool
    resume_execution_only: bool