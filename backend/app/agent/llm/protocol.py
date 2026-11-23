from typing import Protocol

from app.agent.schemas.plan import TaskIntent, TaskPlan
from app.memory.schemas import PlanningContext


class LLMProvider(Protocol):
    name: str

    async def interpret_intent(
        self, instruction: str, *, context: PlanningContext | None = None
    ) -> TaskIntent: ...

    async def create_plan(
        self, instruction: str, intent: TaskIntent, *, context: PlanningContext | None = None
    ) -> TaskPlan: ...