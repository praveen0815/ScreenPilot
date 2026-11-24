import json
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.enums import StepStatus, TaskStatus
from app.db.models.agent_task import AgentTask
from app.db.models.task_step import TaskStep
from app.db.session import get_engine


def _auth_headers(client, email: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "valid-passphrase-1",
            "display_name": email.split("@")[0],
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_workflow_retry_then_complete(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "wf-retry@example.com")
    created = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "workflow-retry status check"},
    )
    task_id = created.json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    assert run.json()["status"] == "completed"
    assert "Workflow completed" in run.json()["outcome"]["message"]

    detail = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert len(detail.json()["tool_executions"]) >= 3


@pytest.mark.asyncio
async def test_workflow_conditional_skips_branch(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "wf-cond@example.com")
    created = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "workflow-conditional report"},
    )
    task_id = created.json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    assert run.json()["status"] == "completed"

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        steps = (
            await session.scalars(select(TaskStep).where(TaskStep.task_id == uuid.UUID(task_id)))
        ).all()
        by_seq = {row.sequence: row for row in steps}
        assert by_seq[2].status == StepStatus.SKIPPED
        assert by_seq[3].status == StepStatus.COMPLETED


@pytest.mark.asyncio
async def test_workflow_resume_after_pause(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "wf-pause@example.com")
    created = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "workflow-retry pause test"},
    )
    task_id = created.json()["id"]

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        task = await session.get(AgentTask, uuid.UUID(task_id))
        task.pause_requested = True
        await session.commit()

    first = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "paused"

    resumed = client.post(f"/api/tasks/{task_id}/resume", headers=headers)
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_workflow_persists_state(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "wf-state@example.com")
    created = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "workflow-retry persist"},
    )
    task_id = created.json()["id"]
    client.post(f"/api/tasks/{task_id}/run", headers=headers)

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        task = await session.get(AgentTask, uuid.UUID(task_id))
        assert task.workflow_state_json is not None
        state = json.loads(task.workflow_state_json)
        assert state["execution_budget_used"] >= 2