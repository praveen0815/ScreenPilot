import json
import uuid

import pytest
from starlette.testclient import TestClient

from app.events.broker import get_task_event_broker


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
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


def _token(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "valid-passphrase-1",
            "display_name": email.split("@")[0],
        },
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_task_events_rest_requires_auth(sqlite_app_client):
    client = sqlite_app_client
    task_id = str(uuid.uuid4())
    denied = client.get(f"/api/tasks/{task_id}/events")
    assert denied.status_code == 401


@pytest.mark.asyncio
async def test_task_events_rest_isolation(sqlite_app_client):
    client = sqlite_app_client
    h1 = _auth_headers(client, "evt-a@example.com")
    h2 = _auth_headers(client, "evt-b@example.com")
    t1 = client.post("/api/tasks", headers=h1, json={"instruction": "events isolation a"}).json()["id"]
    client.post("/api/tasks", headers=h2, json={"instruction": "events isolation b"})
    forbidden = client.get(f"/api/tasks/{t1}/events", headers=h2)
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_task_run_emits_ordered_events(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "evt-order@example.com")
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "workflow-retry status check"},
    ).json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200

    events = client.get(f"/api/tasks/{task_id}/events", headers=headers).json()
    assert len(events) >= 3
    sequences = [row["sequence"] for row in events]
    assert sequences == sorted(sequences)
    assert sequences[0] == 1
    types = [row["type"] for row in events]
    assert types[0] == "task_created"
    assert "planning_started" in types
    assert "task_completed" in types


@pytest.mark.asyncio
async def test_ws_auth_rejects_missing_token(sqlite_app_client):
    client = sqlite_app_client
    with client.websocket_connect("/api/ws/events") as ws:
        frame = ws.receive_json()
        assert frame["type"] == "error"


@pytest.mark.asyncio
async def test_ws_backlog_delivery_after_run(sqlite_app_client):
    client = sqlite_app_client
    token = _token(client, "evt-ws@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "workflow-retry live"},
    ).json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    persisted = client.get(f"/api/tasks/{task_id}/events", headers=headers).json()

    received: list[dict] = []
    with client.websocket_connect(f"/api/ws/events?token={token}&task_id={task_id}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        for _ in range(len(persisted)):
            frame = ws.receive_json()
            if frame.get("type") == "event" and frame.get("event"):
                received.append(frame["event"])

    assert any(row["type"] == "task_created" for row in received)
    assert any(row["type"] == "task_completed" for row in received)
    sequences = [row["sequence"] for row in received]
    assert sequences == sorted(sequences)


@pytest.mark.asyncio
async def test_ws_resume_replays_after_sequence(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "evt-resume@example.com")
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "workflow-retry resume events"},
    ).json()["id"]
    client.post(f"/api/tasks/{task_id}/run", headers=headers)
    persisted = client.get(f"/api/tasks/{task_id}/events", headers=headers).json()
    assert len(persisted) >= 2
    last_sequence = persisted[-1]["sequence"]

    token = headers["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(f"/api/ws/events?token={token}&task_id={task_id}") as ws:
        ws.receive_json()
        for _ in range(len(persisted)):
            ws.receive_json()

        ws.send_json({"type": "resume", "task_id": task_id, "last_sequence": 0})
        replayed: list[dict] = []
        for _ in range(len(persisted)):
            frame = ws.receive_json()
            if frame.get("type") == "event" and frame.get("event"):
                replayed.append(frame["event"])

        assert len(replayed) >= len(persisted)
        assert replayed[0]["sequence"] == 1
        assert replayed[-1]["sequence"] == last_sequence


@pytest.mark.asyncio
async def test_publish_sanitizes_secrets_in_payload(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "evt-sanitize@example.com")
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "secret payload test"},
    ).json()["id"]

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.db.session import get_engine
    from app.events.schemas import TaskEventType
    from app.events.service import publish_task_event

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    user_id = uuid.UUID(
        client.get("/api/users/me", headers=headers).json()["id"]
    )

    async with session_factory() as session:
        await publish_task_event(
            session,
            user_id=user_id,
            task_id=uuid.UUID(task_id),
            event_type=TaskEventType.PLANNING_STARTED,
            payload={"message": "ok password=super-secret-value"},
        )
        await session.commit()

    events = client.get(f"/api/tasks/{task_id}/events", headers=headers).json()
    secret_event = next(row for row in events if row["type"] == "planning_started" and row["sequence"] > 1)
    message = secret_event["payload"].get("message") or ""
    assert "super-secret-value" not in message
    assert "[redacted]" in message