import base64
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.memory.errors import MemoryPolicyError
from app.memory.sanitize import sanitize_text_for_memory
from app.memory.service import MemoryService
from app.db.enums import MemoryEntryKind, MemoryScope, TaskStatus
from app.db.models.agent_task import AgentTask
from app.db.models.task_memory_entry import TaskMemoryEntry
from app.core.config import get_settings


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


def test_sanitize_rejects_tokens_and_passwords():
    with pytest.raises(MemoryPolicyError):
        sanitize_text_for_memory("password=secret123", max_chars=100)
    with pytest.raises(MemoryPolicyError):
        sanitize_text_for_memory("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhIjoxfQ.x", max_chars=200)


def test_sanitize_strips_large_base64():
    blob = base64.b64encode(b"x" * 256).decode()
    cleaned = sanitize_text_for_memory(f"shot:{blob}", max_chars=2000)
    assert "[redacted-base64]" in cleaned


@pytest.mark.asyncio
async def test_memory_task_isolation(sqlite_app_client):
    client = sqlite_app_client
    h1 = _auth_headers(client, "mem-a@example.com")
    h2 = _auth_headers(client, "mem-b@example.com")
    t1 = client.post("/api/tasks", headers=h1, json={"instruction": "Task for user A"}).json()["id"]
    t2 = client.post("/api/tasks", headers=h2, json={"instruction": "Task for user B"}).json()["id"]

    client.post(f"/api/tasks/{t1}/run", headers=h1)
    mem_a = client.get(f"/api/tasks/{t1}/memory", headers=h1)
    assert mem_a.status_code == 200
    assert mem_a.json()["total_entries"] >= 2

    blocked = client.get(f"/api/tasks/{t1}/memory", headers=h2)
    assert blocked.status_code == 404

    mem_b = client.get(f"/api/tasks/{t2}/memory", headers=h2)
    assert mem_b.status_code == 200
    assert mem_b.json()["task_id"] == t2


@pytest.mark.asyncio
async def test_clear_task_memory(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "clear-mem@example.com")
    task_id = client.post("/api/tasks", headers=headers, json={"instruction": "Clearable task"}).json()["id"]
    client.post(f"/api/tasks/{task_id}/run", headers=headers)
    before = client.get(f"/api/tasks/{task_id}/memory", headers=headers).json()["total_entries"]
    assert before > 0
    cleared = client.delete(f"/api/tasks/{task_id}/memory", headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["removed_entries"] == before
    after = client.get(f"/api/tasks/{task_id}/memory", headers=headers).json()
    assert after["total_entries"] == 0
    assert after["task_summary"] is None


@pytest.mark.asyncio
async def test_user_preferences_persist(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "prefs@example.com")
    updated = client.patch(
        "/api/users/me/preferences",
        headers=headers,
        json={"preferences": {"verbosity": "brief", "language": "en"}},
    )
    assert updated.status_code == 200
    assert updated.json()["preferences"]["verbosity"] == "brief"
    blocked = client.patch(
        "/api/users/me/preferences",
        headers=headers,
        json={"preferences": {"password": "x"}},
    )
    assert blocked.status_code == 400


@pytest.mark.asyncio
async def test_memory_limits_and_expiry():
    os.environ["MEMORY_MAX_ENTRIES_PER_TASK"] = "10"
    get_settings.cache_clear()
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.db.base import Base
    from app.db.enums import UserRole
    from app.db.models.user import User
    from app.db.session import configure_engine, dispose_engine, get_engine

    configure_engine("sqlite+aiosqlite:///:memory:")
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        user = User(
            email="limit@example.com",
            password_hash="not-real-hash-value",
            display_name="limit",
            role=UserRole.USER,
        )
        session.add(user)
        await session.flush()
        task = AgentTask(user_id=user.id, instruction="limit test", status=TaskStatus.PENDING)
        session.add(task)
        await session.flush()
        memory = MemoryService(session)
        for index in range(12):
            await memory._add(
                user=user,
                task=task,
                scope=MemoryScope.TASK,
                kind=MemoryEntryKind.SHORT_TERM,
                content=f"entry-{index}",
            )
        bundle = await memory.get_task_memory(user, task)
        assert bundle.total_entries <= 10

        expired = TaskMemoryEntry(
            user_id=user.id,
            task_id=task.id,
            scope=MemoryScope.TASK,
            kind=MemoryEntryKind.SHORT_TERM,
            content="old",
            content_chars=3,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        session.add(expired)
        await session.flush()
        removed = await memory.cleanup_expired(user.id)
        assert removed >= 1
    await dispose_engine()
    os.environ.pop("MEMORY_MAX_ENTRIES_PER_TASK", None)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_planning_context_window(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "ctx@example.com")
    client.patch(
        "/api/users/me/preferences",
        headers=headers,
        json={"preferences": {"verbosity": "brief"}},
    )
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "Use memory in planning"},
    ).json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    memory = client.get(f"/api/tasks/{task_id}/memory", headers=headers).json()
    assert memory["total_entries"] >= 1
    assert any("conversation" in str(item.get("kind", "")) for item in memory["conversation"])