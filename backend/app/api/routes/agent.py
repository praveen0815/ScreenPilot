from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.boundary import LangGraphRuntimeBoundary
from app.auth.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.agent import AgentTask as AgentTaskPayload
from app.schemas.agent import CreateAgentRunRequest, RunTaskResponse
from app.services import task_service

router = APIRouter(tags=["agent"])


@router.post("/api/agent/runs", response_model=RunTaskResponse)
async def create_agent_run(
    body: CreateAgentRunRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RunTaskResponse:
    """Create a task and run the mock LangGraph agent (no real LLM)."""

    task = await task_service.create_task(session, current_user, instruction=body.instruction)
    await session.flush()
    outcome = await LangGraphRuntimeBoundary().run(
        AgentTaskPayload(task_id=task.id, instruction=task.instruction),
        session=session,
        user=current_user,
    )
    await session.refresh(task)
    return RunTaskResponse(task_id=task.id, status=task.status, outcome=outcome)