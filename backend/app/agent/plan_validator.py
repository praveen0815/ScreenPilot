import json

from pydantic import ValidationError

from app.agent.schemas.plan import TaskPlan, registered_tool_names
from app.workflow.dependencies import WorkflowDependencyError, validate_step_dependencies
from app.safety.risk import ActionRiskLevel, classify_tool
from app.tools.contracts import ToolRisk
from app.tools.registry import build_registry
from app.core.config import get_settings


class PlanValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def validate_plan(plan: TaskPlan) -> None:
    settings = get_settings()
    if len(plan.steps) > settings.agent_max_plan_steps:
        raise PlanValidationError("Plan has too many steps.")
    try:
        validate_step_dependencies(plan)
    except WorkflowDependencyError as exc:
        raise PlanValidationError(exc.message) from exc
    registry = build_registry()
    allowed = registered_tool_names()
    for step in plan.steps:
        if step.tool_name not in allowed:
            raise PlanValidationError(f"Tool '{step.tool_name}' is not allowed in this build.")
        metadata = next(
            (item for item in registry.list_metadata() if item.name == step.tool_name),
            None,
        )
        if metadata is None or not metadata.available:
            raise PlanValidationError(f"Tool '{step.tool_name}' is not available.")
        action_level = classify_tool(metadata)
        if action_level is ActionRiskLevel.RESTRICTED:
            raise PlanValidationError(f"Tool '{step.tool_name}' is restricted and cannot be planned.")
        if metadata.risk is ToolRisk.HIGH and step.risk is not ToolRisk.HIGH:
            raise PlanValidationError(
                f"Tool '{step.tool_name}' is high-risk and must have a high-risk plan step."
            )
        if "shell" in step.arguments or "command" in step.arguments:
            raise PlanValidationError("Plan arguments may not include shell fields.")
    try:
        TaskPlan.model_validate(json.loads(plan.model_dump_json()))
    except ValidationError as exc:
        raise PlanValidationError(str(exc)) from exc