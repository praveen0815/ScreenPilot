import asyncio
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from app.automation.browser import BrowserAction, BrowserAutomationUnavailable, BrowserCommand
from app.automation.desktop import DesktopAction, DesktopAutomationUnavailable, DesktopCommand
from app.automation.vision import (
    OcrRequest,
    ScreenImage,
    ScreenUnderstandingUnavailable,
    VisionQuestion,
)
from app.core.errors import AutomationUnavailableError, UnknownToolError
from app.auth.permissions import ROLE_PERMISSIONS
from app.db.enums import UserRole
from app.tools.base import BaseTool
from app.tools.contracts import ToolContext as ToolRunContext, ToolMetadata, ToolRisk
from app.tools.executor_service import ToolExecutorService
from app.tools.registry import ToolRegistry, build_registry


def test_browser_rejects_shell_and_non_http_navigation():
    with pytest.raises(ValidationError):
        BrowserCommand.model_validate({"action": "run_shell", "command": "whoami"})
    with pytest.raises(ValidationError):
        BrowserCommand.model_validate({"action": "navigate", "url": "javascript:alert(1)"})
    with pytest.raises(ValidationError):
        BrowserCommand.model_validate({"action": "navigate", "url": "file:///c/windows"})
    with pytest.raises(ValidationError):
        BrowserCommand.model_validate({"action": "navigate", "url": "https://example.com", "shell": "x"})


def test_browser_accepts_absolute_http_url():
    command = BrowserCommand.model_validate(
        {"action": "navigate", "url": "https://example.com/reports"}
    )

    assert command.action is BrowserAction.NAVIGATE


def test_browser_engine_does_not_execute():
    command = BrowserCommand(action=BrowserAction.SNAPSHOT)

    with pytest.raises(AutomationUnavailableError):
        asyncio.run(BrowserAutomationUnavailable().execute(command))


def test_desktop_rejects_shell_field_and_accepts_screenshot():
    with pytest.raises(ValidationError):
        DesktopCommand.model_validate({"action": "run_shell"})
    with pytest.raises(ValidationError):
        DesktopCommand.model_validate({"action": "screenshot", "command": "calc.exe"})
    with pytest.raises(ValidationError):
        DesktopCommand.model_validate({"action": "hotkey", "keys": ["rm -rf"]})

    command = DesktopCommand(action=DesktopAction.SCREENSHOT)
    assert command.action is DesktopAction.SCREENSHOT


def test_desktop_engine_does_not_execute():
    command = DesktopCommand(action=DesktopAction.SCREENSHOT)

    with pytest.raises(AutomationUnavailableError):
        asyncio.run(DesktopAutomationUnavailable().execute(command))


def test_vision_engine_does_not_read_the_image():
    image = ScreenImage(content_type="image/png", data_base64="aGVsbG8=")
    engine = ScreenUnderstandingUnavailable()

    with pytest.raises(AutomationUnavailableError):
        asyncio.run(engine.extract_text(OcrRequest(image=image)))
    with pytest.raises(AutomationUnavailableError):
        asyncio.run(engine.answer(VisionQuestion(image=image, question="What is on screen?")))


class FlagInput(BaseModel):
    pass


class FlagOutput(BaseModel):
    executed: bool = True


class FlagTool(BaseTool):
    called = False

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="flag",
            version="1.0.0",
            description="Records whether execute was called.",
            risk=ToolRisk.LOW,
            timeout_seconds=1.0,
            input_schema="FlagInput",
            output_schema="FlagOutput",
        )

    @property
    def input_model(self):
        return FlagInput

    @property
    def output_model(self):
        return FlagOutput

    async def invoke(self, payload, context):
        del payload, context
        FlagTool.called = True
        return FlagOutput()


def test_default_registry_registers_safe_and_mock_tools():
    specs = build_registry().list_specs()
    names = {item.name for item in specs}
    assert "mock.observe" in names
    assert "tool.current_time" in names
    assert "tool.text_transform" in names


def test_registry_rejects_duplicates_and_unknown_names():
    registry = ToolRegistry()
    registry.register(FlagTool())

    with pytest.raises(ValueError):
        registry.register(FlagTool())
    with pytest.raises(UnknownToolError):
        registry.get("missing")


def test_tool_executor_runs_registered_mock_tools():
    registry = build_registry()
    context = ToolRunContext(
        task_id=uuid4(),
        user_id=uuid4(),
        permissions=ROLE_PERMISSIONS[UserRole.USER],
        confirmed=True,
    )
    result = asyncio.run(
        ToolExecutorService().execute("mock.observe", {"target": "status"}, context, registry)
    )
    assert result.success is True
