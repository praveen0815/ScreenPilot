import asyncio
import os
from uuid import uuid4

import pytest

from app.auth.permissions import ROLE_PERMISSIONS
from app.automation.desktop.hotkeys import validate_hotkey
from app.automation.desktop.safety import get_desktop_safety_gate
from app.automation.desktop.service import get_desktop_automation_service, reset_desktop_adapter_for_tests
from app.core.config import get_settings
from app.db.enums import UserRole
from app.tools.contracts import ToolContext
from app.tools.executor_service import ToolExecutorService
from app.tools.registry import build_registry


@pytest.fixture
def desktop_env():
    os.environ["DESKTOP_ENABLED"] = "true"
    os.environ["DESKTOP_ADAPTER"] = "mock"
    get_settings.cache_clear()
    reset_desktop_adapter_for_tests()
    gate = get_desktop_safety_gate()
    gate.clear_emergency_stop()
    yield
    gate.clear_emergency_stop()
    reset_desktop_adapter_for_tests()
    os.environ["DESKTOP_ENABLED"] = "false"
    get_settings.cache_clear()


def _context(*, confirmed: bool = True) -> ToolContext:
    return ToolContext(
        task_id=uuid4(),
        user_id=uuid4(),
        permissions=ROLE_PERMISSIONS[UserRole.USER],
        confirmed=confirmed,
    )


def test_hotkey_allowlist_blocks_sensitive_combos():
    with pytest.raises(Exception):
        validate_hotkey(["alt", "f4"])
    with pytest.raises(Exception):
        validate_hotkey(["win", "d"])


def test_hotkey_allowlist_accepts_ctrl_c():
    assert validate_hotkey(["ctrl", "c"]) == ("ctrl", "c")


@pytest.mark.asyncio
async def test_desktop_bounds_validation(desktop_env):
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context()

    out_of_bounds = await executor.execute(
        "tool.desktop.mouse.click",
        {"x": 5000, "y": 5000, "button": "left"},
        context,
        registry,
    )
    assert out_of_bounds.success is False


@pytest.mark.asyncio
async def test_desktop_high_risk_requires_confirmation(desktop_env):
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context(confirmed=False)

    click = await executor.execute(
        "tool.desktop.mouse.click",
        {"x": 100, "y": 100, "button": "left"},
        context,
        registry,
    )
    assert click.success is False
    assert click.error_code == "tool_permission_denied"


@pytest.mark.asyncio
async def test_desktop_mock_adapter_flow(desktop_env):
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context()

    info = await executor.execute("tool.desktop.display.info", {}, context, registry)
    assert info.success is True
    assert info.data == {"width": 1920, "height": 1080}

    shot = await executor.execute("tool.desktop.screenshot", {}, context, registry)
    assert shot.success is True
    assert shot.data["byte_length"] > 0

    move = await executor.execute("tool.desktop.mouse.move", {"x": 200, "y": 300}, context, registry)
    assert move.success is True

    pos = await executor.execute("tool.desktop.mouse.position", {}, context, registry)
    assert pos.data == {"x": 200, "y": 300}


@pytest.mark.asyncio
async def test_emergency_stop_blocks_desktop_actions(desktop_env):
    gate = get_desktop_safety_gate()
    gate.activate_emergency_stop()
    service = get_desktop_automation_service()
    task_id = uuid4()

    with pytest.raises(Exception):
        await service.screenshot(task_id)


@pytest.mark.asyncio
async def test_task_cancellation_blocks_actions(desktop_env):
    gate = get_desktop_safety_gate()
    task_id = uuid4()
    gate.cancel_task(task_id)
    service = get_desktop_automation_service()

    with pytest.raises(Exception):
        await service.display_info(task_id)


def test_invalid_desktop_tool_input(desktop_env):
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context()

    bad = asyncio.run(
        executor.execute(
            "tool.desktop.keyboard.hotkey",
            {"keys": []},
            context,
            registry,
        )
    )
    assert bad.success is False
    assert bad.error_code == "tool_validation_error"