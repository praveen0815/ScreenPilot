"""LangGraph agent boundary."""

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import AgentOrchestrator
from app.core.config import get_settings
from app.db.models.user import User
from app.schemas.agent import AgentOutcome
from app.schemas.agent import AgentTask as AgentTaskPayload


class LangGraphRuntimeBoundary:
    name = "agent"
    detail = "LangGraph planning and mock tool execution (mock LLM provider only)."

    def availability(self) -> Literal["mock"]:
        settings = get_settings()
        if settings.llm_provider.strip().lower() != "mock":
            return "mock"
        return "mock"

    async def run(
        self,
        payload: AgentTaskPayload,
        *,
        session: AsyncSession,
        user: User,
    ) -> AgentOutcome:
        orchestrator = AgentOrchestrator(session)
        return await orchestrator.run_task(user, payload.task_id)