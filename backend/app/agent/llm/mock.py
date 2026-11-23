"""Deterministic mock LLM for tests and development. This is not a real model."""

from app.agent.schemas.plan import PlanStepSpec, TaskIntent, TaskPlan
from app.memory.schemas import PlanningContext
from app.tools.contracts import ToolRisk


class MockLLMProvider:
    name = "mock"

    async def interpret_intent(
        self, instruction: str, *, context: PlanningContext | None = None
    ) -> TaskIntent:
        lowered = instruction.lower()
        constraints: list[str] = []
        if "do not" in lowered or "without" in lowered:
            constraints.append("Follow user constraints from the instruction.")
        if context:
            if context.user_preferences.get("verbosity") == "brief":
                constraints.append("Prefer brief planner output.")
            if context.task_summary:
                constraints.append(f"Prior task summary: {context.task_summary[:200]}")
            for line in context.conversation_turns[-3:]:
                constraints.append(f"Conversation context: {line[:160]}")
            for line in context.recent_tool_results[-3:]:
                constraints.append(f"Recent tool: {line[:160]}")
        return TaskIntent(
            summary=f"User wants help with: {instruction[:200]}",
            objective=instruction.strip()[:500],
            constraints=constraints[:10],
        )

    async def create_plan(
        self, instruction: str, intent: TaskIntent, *, context: PlanningContext | None = None
    ) -> TaskPlan:
        del context
        lowered = instruction.lower()
        if "planner-error" in lowered:
            raise RuntimeError("Mock planner simulated a model failure.")
        if "plan-invalid" in lowered:
            return TaskPlan(
                goal=intent.objective,
                steps=[
                    PlanStepSpec(
                        sequence=1,
                        description="Attempt forbidden shell field",
                        tool_name="mock.observe",
                        arguments={"target": "x", "shell": "whoami"},
                        risk=ToolRisk.LOW,
                    )
                ],
            )

        risk = ToolRisk.HIGH if any(word in lowered for word in ("purchase", "buy", "pay")) else ToolRisk.LOW
        steps = [
            PlanStepSpec(
                sequence=1,
                description="Read application status for context",
                tool_name="tool.app_status",
                arguments={},
                risk=ToolRisk.LOW,
            ),
            PlanStepSpec(
                sequence=2,
                description="Transform the intent summary for the user",
                tool_name="tool.text_transform",
                arguments={"operation": "trim", "text": intent.summary},
                risk=ToolRisk.HIGH if risk is ToolRisk.HIGH else ToolRisk.LOW,
            ),
        ]
        return TaskPlan(goal=intent.objective, steps=steps)