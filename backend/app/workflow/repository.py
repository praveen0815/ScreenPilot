import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_task import AgentTask
from app.workflow.schemas import WorkflowState


def load_workflow_state(task: AgentTask) -> WorkflowState:
    raw = task.workflow_state_json
    if not raw:
        return WorkflowState()
    try:
        return WorkflowState.model_validate(json.loads(raw))
    except Exception:
        return WorkflowState()


async def persist_workflow_state(session: AsyncSession, task: AgentTask, state: WorkflowState) -> None:
    task.workflow_state_json = state.model_dump_json()
    await session.flush()