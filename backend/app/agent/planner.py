from app.agent.llm.protocol import LLMProvider
from app.agent.schemas.plan import TaskIntent, TaskPlan
from app.core.config import get_settings
from app.memory.schemas import PlanningContext
from pydantic import ValidationError

from app.agent.schemas.plan import TaskPlan as TaskPlanModel


async def interpret_intent(
    provider: LLMProvider,
    instruction: str,
    *,
    context: PlanningContext | None = None,
) -> TaskIntent:
    return await provider.interpret_intent(instruction, context=context)


async def build_plan(
    provider: LLMProvider,
    instruction: str,
    intent: TaskIntent,
    *,
    context: PlanningContext | None = None,
) -> TaskPlan:
    raw = await provider.create_plan(instruction, intent, context=context)
    settings = get_settings()
    if len(raw.steps) > settings.agent_max_plan_steps:
        raise ValidationError.from_exception_data(
            "TaskPlan",
            [{"type": "too_long", "loc": ("steps",), "msg": "Plan exceeds step limit."}],
        )
    return TaskPlanModel.model_validate(raw.model_dump())