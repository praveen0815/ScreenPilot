import pytest

from app.agent.state_machine import ALLOWED_TRANSITIONS, transition
from app.db.enums import TaskStatus


def _auth_headers(client, email: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "valid-passphrase-1",
            "display_name": email.split("@")[0],
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_task_creation_and_planning_output(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "planner@example.com")
    created = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "Summarize the weekly status report"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    body = run.json()
    assert body["status"] == "completed"
    assert body["outcome"]["status"] == "completed"

    detail = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert len(payload["steps"]) == 2
    assert payload["steps"][0]["tool_name"] == "tool.app_status"
    assert len(payload["tool_executions"]) == 2


@pytest.mark.asyncio
async def test_invalid_plan_rejection(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "invalid@example.com")
    created = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "plan-invalid should fail validation"},
    )
    task_id = created.json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    assert run.json()["status"] == "failed"
    assert run.json()["outcome"]["status"] == "failed"


@pytest.mark.asyncio
async def test_failed_planning(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "failplan@example.com")
    created = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "trigger planner-error in mock"},
    )
    task_id = created.json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200, run.text
    assert run.json()["status"] == "failed"
    assert run.json()["outcome"]["status"] == "failed"
    assert "planning" in run.json()["outcome"]["message"].lower() or "failed" in run.json()["outcome"]["message"].lower()


def test_state_transition_table():
    transition(TaskStatus.PENDING, TaskStatus.PLANNING)
    transition(TaskStatus.PLANNING, TaskStatus.RUNNING)
    transition(TaskStatus.RUNNING, TaskStatus.COMPLETED)
    assert TaskStatus.AWAITING_APPROVAL in ALLOWED_TRANSITIONS[TaskStatus.PLANNING]


@pytest.mark.asyncio
async def test_cancellation_before_run(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "cancel@example.com")
    created = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "Do a harmless task"},
    )
    task_id = created.json()["id"]
    cancel = client.post(f"/api/tasks/{task_id}/cancel", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 409


@pytest.mark.asyncio
async def test_awaiting_approval_and_resume(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "buyer@example.com")
    created = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "purchase the premium license"},
    )
    task_id = created.json()["id"]
    first = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "awaiting_approval"
    assert first.json()["outcome"]["status"] == "needs_user"

    blocked = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert blocked.status_code == 409

    approve = client.post(f"/api/tasks/{task_id}/approve", headers=headers)
    assert approve.status_code == 200

    resumed = client.post(f"/api/tasks/{task_id}/resume", headers=headers)
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_mock_executor_records_tool_runs(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "mockexec@example.com")
    run = client.post(
        "/api/agent/runs",
        headers=headers,
        json={"instruction": "Check project status"},
    )
    assert run.status_code == 200
    task_id = run.json()["task_id"]
    detail = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert all(row["status"] == "succeeded" for row in detail.json()["tool_executions"])