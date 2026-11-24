"""Controlled end-to-end scenarios (mock LLM + real HTTP API + SQLite DB)."""

import os
import threading
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.enums import TaskStatus
from app.db.models.agent_task import AgentTask
from app.db.session import get_engine

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "browser"


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


@pytest.fixture(scope="module")
def browser_test_page_url() -> str:
    class _Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(FIXTURES_DIR), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}/page.html"
    yield url
    server.shutdown()


@pytest.fixture
def browser_env(browser_test_page_url):
    del browser_test_page_url
    os.environ["BROWSER_ENABLED"] = "true"
    os.environ["BROWSER_ALLOW_LOCALHOST"] = "true"
    get_settings.cache_clear()
    yield
    os.environ["BROWSER_ENABLED"] = "false"
    os.environ["BROWSER_ALLOW_LOCALHOST"] = "false"
    get_settings.cache_clear()


async def _chromium_ready() -> bool:
    try:
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        await browser.close()
        await playwright.stop()
        return True
    except Exception:
        return False


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_01_user_creates_simple_task(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "e2e-create@example.com")
    created = client.post("/api/tasks", headers=headers, json={"instruction": "Summarize the weekly update"})
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "pending"
    assert body["instruction"].startswith("Summarize")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_02_agent_generates_plan(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "e2e-plan@example.com")
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "Summarize the weekly update"},
    ).json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    detail = client.get(f"/api/tasks/{task_id}", headers=headers).json()
    assert len(detail["steps"]) == 2
    assert detail["steps"][0]["tool_name"] == "tool.app_status"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_03_calculator_tool_and_04_completion_report(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "e2e-calc@example.com")
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "e2e-calculator compute total"},
    ).json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    assert run.json()["status"] == "completed"
    detail = client.get(f"/api/tasks/{task_id}", headers=headers).json()
    calc_runs = [row for row in detail["tool_executions"] if row["tool_name"] == "tool.calculate"]
    assert calc_runs
    assert calc_runs[0]["status"] == "succeeded"
    assert run.json()["outcome"]["status"] == "completed"


@pytest.mark.e2e
@pytest.mark.browser
@pytest.mark.asyncio
async def test_scenario_05_through_08_browser_task_extract_and_report(
    sqlite_app_client, browser_env, browser_test_page_url
):
    if not await _chromium_ready():
        pytest.skip("Playwright Chromium is not installed.")

    client = sqlite_app_client
    headers = _auth_headers(client, "e2e-browser@example.com")
    instruction = f"e2e-browser extract heading from {browser_test_page_url}"
    task_id = client.post("/api/tasks", headers=headers, json={"instruction": instruction}).json()["id"]

    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    assert run.json()["status"] == "completed", run.text

    detail = client.get(f"/api/tasks/{task_id}", headers=headers).json()
    browser_tools = {row["tool_name"] for row in detail["tool_executions"]}
    assert "tool.browser.navigate" in browser_tools
    assert "tool.browser.text" in browser_tools
    text_run = next(row for row in detail["tool_executions"] if row["tool_name"] == "tool.browser.text")
    assert text_run["status"] == "succeeded"
    assert "Hello Browser" in (text_run["result_json"] or "")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_09_risky_action_triggers_approval(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "e2e-approve@example.com")
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "purchase premium plan"},
    ).json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    assert run.json()["status"] == "awaiting_approval"
    pending = client.get(f"/api/tasks/{task_id}/approvals", headers=headers).json()["approvals"]
    assert pending and pending[0]["status"] == "pending"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_10_rejected_approval_blocks_execution(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "e2e-reject@example.com")
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "purchase addon pack"},
    ).json()["id"]
    client.post(f"/api/tasks/{task_id}/run", headers=headers)
    approval_id = client.get(f"/api/tasks/{task_id}/approvals", headers=headers).json()["approvals"][0]["id"]
    client.post(
        f"/api/tasks/{task_id}/approvals/{approval_id}/reject",
        headers=headers,
        json={"reason": "Not authorized"},
    )
    detail = client.get(f"/api/tasks/{task_id}", headers=headers).json()
    assert detail["status"] == "failed"
    resume = client.post(f"/api/tasks/{task_id}/resume", headers=headers)
    assert resume.status_code == 409


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_11_cancellation_stops_task(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "e2e-cancel@example.com")
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "workflow-retry pause test"},
    ).json()["id"]

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        task = await session.get(AgentTask, uuid.UUID(task_id))
        task.pause_requested = True
        await session.commit()

    pause_run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert pause_run.status_code == 200
    assert pause_run.json()["status"] == "paused"

    cancel = client.post(f"/api/tasks/{task_id}/cancel", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    resume = client.post(f"/api/tasks/{task_id}/resume", headers=headers)
    assert resume.status_code == 409


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_12_failed_tool_handled_safely(sqlite_app_client):
    client = sqlite_app_client
    headers = _auth_headers(client, "e2e-fail@example.com")
    task_id = client.post(
        "/api/tasks",
        headers=headers,
        json={"instruction": "e2e-tool-fail safe handling"},
    ).json()["id"]
    run = client.post(f"/api/tasks/{task_id}/run", headers=headers)
    assert run.status_code == 200
    assert run.json()["status"] == "failed"
    detail = client.get(f"/api/tasks/{task_id}", headers=headers).json()
    calc = [row for row in detail["tool_executions"] if row["tool_name"] == "tool.calculate"]
    assert len(calc) >= 2
    assert calc[0]["status"] == "succeeded"
    assert calc[1]["status"] == "failed"
    assert detail["status"] == TaskStatus.FAILED.value