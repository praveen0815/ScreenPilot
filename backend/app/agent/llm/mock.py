"""Deterministic mock LLM for tests and development. This is not a real model."""

import re

from app.agent.schemas.plan import PlanStepSpec, TaskIntent, TaskPlan
from app.memory.schemas import PlanningContext
from app.tools.contracts import ToolRisk
from app.workflow.schemas import WorkflowRunWhen


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
        if "workflow-retry" in lowered:
            return TaskPlan(
                goal=intent.objective,
                steps=[
                    PlanStepSpec(
                        sequence=1,
                        description="Probe with controlled failure then success",
                        tool_name="mock.workflow.attempt",
                        arguments={"probe": "retry", "fail_until_attempt": 2},
                        retry_max=2,
                        retry_backoff_seconds=0.01,
                    ),
                    PlanStepSpec(
                        sequence=2,
                        description="Summarize workflow",
                        tool_name="mock.summarize",
                        arguments={"text": "workflow retry path complete"},
                        depends_on=[1],
                    ),
                ],
            )
        if "workflow-conditional" in lowered:
            return TaskPlan(
                goal=intent.objective,
                steps=[
                    PlanStepSpec(
                        sequence=1,
                        description="Initial observe",
                        tool_name="mock.observe",
                        arguments={"target": "status"},
                    ),
                    PlanStepSpec(
                        sequence=2,
                        description="Only on failure path",
                        tool_name="mock.observe",
                        arguments={"target": "failure-branch"},
                        run_when=WorkflowRunWhen.ON_PREV_FAILURE,
                    ),
                    PlanStepSpec(
                        sequence=3,
                        description="Only on success path",
                        tool_name="mock.summarize",
                        arguments={"text": "success branch summary"},
                        run_when=WorkflowRunWhen.ON_PREV_SUCCESS,
                        depends_on=[1],
                    ),
                ],
            )
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
        if "e2e-calculator" in lowered:
            return TaskPlan(
                goal=intent.objective,
                steps=[
                    PlanStepSpec(
                        sequence=1,
                        description="Evaluate arithmetic expression",
                        tool_name="tool.calculate",
                        arguments={"expression": "12 * 8"},
                        risk=ToolRisk.LOW,
                    ),
                    PlanStepSpec(
                        sequence=2,
                        description="Report calculation to user",
                        tool_name="mock.summarize",
                        arguments={"text": "Calculator result ready."},
                        depends_on=[1],
                        risk=ToolRisk.LOW,
                    ),
                ],
            )
        if "e2e-tool-fail" in lowered:
            return TaskPlan(
                goal=intent.objective,
                steps=[
                    PlanStepSpec(
                        sequence=1,
                        description="Valid calculation",
                        tool_name="tool.calculate",
                        arguments={"expression": "2 + 2"},
                        risk=ToolRisk.LOW,
                    ),
                    PlanStepSpec(
                        sequence=2,
                        description="Unsafe expression must fail safely",
                        tool_name="tool.calculate",
                        arguments={"expression": "__import__('os')"},
                        depends_on=[1],
                        risk=ToolRisk.LOW,
                    ),
                ],
            )
        match = re.search(r"https?://\S+", instruction)
        if "e2e-browser" in lowered and match:
            page_url = match.group(0).rstrip(").,]")
            return TaskPlan(
                goal=intent.objective,
                steps=[
                    PlanStepSpec(
                        sequence=1,
                        description="Open browser session",
                        tool_name="tool.browser.session.create",
                        arguments={},
                        risk=ToolRisk.LOW,
                    ),
                    PlanStepSpec(
                        sequence=2,
                        description="Navigate to local test page",
                        tool_name="tool.browser.navigate",
                        arguments={"url": page_url},
                        depends_on=[1],
                        risk=ToolRisk.LOW,
                    ),
                    PlanStepSpec(
                        sequence=3,
                        description="Extract heading text",
                        tool_name="tool.browser.text",
                        arguments={"selector": "h1#heading"},
                        depends_on=[2],
                        risk=ToolRisk.LOW,
                    ),
                    PlanStepSpec(
                        sequence=4,
                        description="Summarize browser extraction",
                        tool_name="mock.summarize",
                        arguments={"text": "Browser extraction complete."},
                        depends_on=[3],
                        risk=ToolRisk.LOW,
                    ),
                    PlanStepSpec(
                        sequence=5,
                        description="Close browser session",
                        tool_name="tool.browser.session.close",
                        arguments={},
                        depends_on=[4],
                        risk=ToolRisk.LOW,
                    ),
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