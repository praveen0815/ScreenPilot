import asyncio
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import pytest

from app.auth.permissions import ROLE_PERMISSIONS
from app.core.config import get_settings
from app.db.enums import UserRole
from app.tools.contracts import ToolContext
from app.tools.executor_service import ToolExecutorService
from app.tools.registry import build_registry

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "browser"


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
    from app.automation.browser.playwright_service import get_browser_automation_service

    asyncio.run(get_browser_automation_service().shutdown())
    os.environ["BROWSER_ENABLED"] = "false"
    os.environ["BROWSER_ALLOW_LOCALHOST"] = "false"
    get_settings.cache_clear()


def _context(*, confirmed: bool = True) -> ToolContext:
    return ToolContext(
        task_id=uuid4(),
        user_id=uuid4(),
        permissions=ROLE_PERMISSIONS[UserRole.USER],
        confirmed=confirmed,
    )


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


@pytest.mark.browser
@pytest.mark.asyncio
async def test_browser_tool_flow(browser_env, browser_test_page_url):
    if not await _chromium_ready():
        pytest.skip("Playwright Chromium is not installed.")

    registry = build_registry()
    executor = ToolExecutorService()
    context = _context(confirmed=True)

    created = await executor.execute("tool.browser.session.create", {}, context, registry)
    assert created.success is True
    session_id = created.data["session_id"]

    navigated = await executor.execute(
        "tool.browser.navigate",
        {"session_id": session_id, "url": browser_test_page_url},
        context,
        registry,
    )
    assert navigated.success is True
    assert "ScreenPilot Browser Test" in navigated.data["title"]

    title = await executor.execute(
        "tool.browser.title",
        {"session_id": session_id},
        context,
        registry,
    )
    assert "ScreenPilot Browser Test" in title.data["title"]

    text = await executor.execute(
        "tool.browser.text",
        {"session_id": session_id},
        context,
        registry,
    )
    assert "Hello Browser" in text.data["text"]

    inspect = await executor.execute(
        "tool.browser.element.inspect",
        {"session_id": session_id, "selector": "#action-btn"},
        context,
        registry,
    )
    assert inspect.data["tag"] == "button"

    await executor.execute(
        "tool.browser.scroll",
        {"session_id": session_id, "selector": "#scroll-target"},
        context,
        registry,
    )

    typed = await executor.execute(
        "tool.browser.type",
        {"session_id": session_id, "selector": "#name-input", "text": "ScreenPilot"},
        context,
        registry,
    )
    assert typed.success is True

    clicked = await executor.execute(
        "tool.browser.click",
        {"session_id": session_id, "selector": "#action-btn"},
        context,
        registry,
    )
    assert clicked.success is True

    await executor.execute(
        "tool.browser.wait",
        {
            "session_id": session_id,
            "selector": "#status",
            "state": "visible",
            "timeout_ms": 5000,
        },
        context,
        registry,
    )

    shot = await executor.execute(
        "tool.browser.screenshot",
        {"session_id": session_id},
        context,
        registry,
    )
    assert shot.success is True
    assert shot.data["byte_length"] > 100

    closed = await executor.execute(
        "tool.browser.session.close",
        {"session_id": session_id},
        context,
        registry,
    )
    assert closed.success is True
    assert closed.data["actions_recorded"] >= 5


@pytest.mark.browser
@pytest.mark.asyncio
async def test_high_risk_click_blocked_without_confirmation(browser_env, browser_test_page_url):
    if not await _chromium_ready():
        pytest.skip("Playwright Chromium is not installed.")

    registry = build_registry()
    executor = ToolExecutorService()
    context = _context(confirmed=False)

    created = await executor.execute("tool.browser.session.create", {}, context, registry)
    session_id = created.data["session_id"]
    await executor.execute(
        "tool.browser.navigate",
        {"session_id": session_id, "url": browser_test_page_url},
        context,
        registry,
    )

    click = await executor.execute(
        "tool.browser.click",
        {"session_id": session_id, "selector": "#action-btn"},
        context,
        registry,
    )
    assert click.success is False
    assert click.error_code == "tool_permission_denied"

    await executor.execute(
        "tool.browser.session.close",
        {"session_id": session_id},
        context,
        registry,
    )