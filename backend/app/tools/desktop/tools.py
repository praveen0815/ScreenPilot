from pydantic import BaseModel

from app.tools.base import BaseTool
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk
from app.tools.desktop.common import desktop_meta, require_task_context, run_desktop, service
from app.tools.desktop.schemas import (
    ClickInput,
    ClickOutput,
    DisplayOutput,
    DoubleClickInput,
    EmptyInput,
    HotkeyInput,
    HotkeyOutput,
    MoveOutput,
    PointInput,
    PositionOutput,
    ScreenshotOutput,
    ScrollInput,
    ScrollOutput,
    TypeInput,
    TypedOutput,
    WaitInput,
    WaitOutput,
    WindowOutput,
)


class DesktopScreenshotTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.screenshot",
            description="Capture a desktop screenshot.",
            risk=ToolRisk.LOW,
            input_schema="EmptyInput",
            output_schema="ScreenshotOutput",
            timeout_seconds=30.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return EmptyInput

    @property
    def output_model(self) -> type[BaseModel]:
        return ScreenshotOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del payload
        task_id = require_task_context(context)
        data = await run_desktop(service().screenshot(task_id))
        return ScreenshotOutput(**data)


class DesktopMousePositionTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.mouse.position",
            description="Read the current mouse position.",
            risk=ToolRisk.LOW,
            input_schema="EmptyInput",
            output_schema="PositionOutput",
            timeout_seconds=10.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return EmptyInput

    @property
    def output_model(self) -> type[BaseModel]:
        return PositionOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del payload
        task_id = require_task_context(context)
        data = await run_desktop(service().mouse_position(task_id))
        return PositionOutput(**data)


class DesktopDisplayInfoTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.display.info",
            description="Read primary display width and height.",
            risk=ToolRisk.LOW,
            input_schema="EmptyInput",
            output_schema="DisplayOutput",
            timeout_seconds=10.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return EmptyInput

    @property
    def output_model(self) -> type[BaseModel]:
        return DisplayOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del payload
        task_id = require_task_context(context)
        data = await run_desktop(service().display_info(task_id))
        return DisplayOutput(**data)


class DesktopActiveWindowTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.window.active",
            description="Read the active window title when supported by the OS.",
            risk=ToolRisk.LOW,
            input_schema="EmptyInput",
            output_schema="WindowOutput",
            timeout_seconds=10.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return EmptyInput

    @property
    def output_model(self) -> type[BaseModel]:
        return WindowOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del payload
        task_id = require_task_context(context)
        data = await run_desktop(service().active_window(task_id))
        return WindowOutput(**data)


class DesktopWaitTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.wait",
            description="Wait for a bounded interval with cancellation checks.",
            risk=ToolRisk.LOW,
            input_schema="WaitInput",
            output_schema="WaitOutput",
            timeout_seconds=70.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return WaitInput

    @property
    def output_model(self) -> type[BaseModel]:
        return WaitOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, WaitInput)
        task_id = require_task_context(context)
        data = await run_desktop(service().wait_ms(task_id, payload.milliseconds))
        return WaitOutput(**data)


class DesktopMoveMouseTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.mouse.move",
            description="Move the mouse to on-screen coordinates.",
            risk=ToolRisk.HIGH,
            input_schema="PointInput",
            output_schema="MoveOutput",
            timeout_seconds=15.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return PointInput

    @property
    def output_model(self) -> type[BaseModel]:
        return MoveOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, PointInput)
        task_id = require_task_context(context)
        data = await run_desktop(service().move_mouse(task_id, payload.x, payload.y))
        return MoveOutput(**data)


class DesktopClickTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.mouse.click",
            description="Click at on-screen coordinates. Requires approval.",
            risk=ToolRisk.HIGH,
            input_schema="ClickInput",
            output_schema="ClickOutput",
            timeout_seconds=15.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return ClickInput

    @property
    def output_model(self) -> type[BaseModel]:
        return ClickOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, ClickInput)
        task_id = require_task_context(context)
        data = await run_desktop(service().click(task_id, payload.x, payload.y, payload.button))
        return ClickOutput(**data)


class DesktopDoubleClickTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.mouse.double_click",
            description="Double-click at on-screen coordinates. Requires approval.",
            risk=ToolRisk.HIGH,
            input_schema="DoubleClickInput",
            output_schema="MoveOutput",
            timeout_seconds=15.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return DoubleClickInput

    @property
    def output_model(self) -> type[BaseModel]:
        return MoveOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, DoubleClickInput)
        task_id = require_task_context(context)
        data = await run_desktop(service().double_click(task_id, payload.x, payload.y))
        return MoveOutput(**data)


class DesktopScrollTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.scroll",
            description="Scroll the mouse wheel. Requires approval.",
            risk=ToolRisk.HIGH,
            input_schema="ScrollInput",
            output_schema="ScrollOutput",
            timeout_seconds=15.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return ScrollInput

    @property
    def output_model(self) -> type[BaseModel]:
        return ScrollOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, ScrollInput)
        task_id = require_task_context(context)
        data = await run_desktop(service().scroll(task_id, payload.delta_y))
        return ScrollOutput(**data)


class DesktopTypeTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.keyboard.type",
            description="Type text at the current focus. Requires approval.",
            risk=ToolRisk.HIGH,
            input_schema="TypeInput",
            output_schema="TypedOutput",
            timeout_seconds=30.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return TypeInput

    @property
    def output_model(self) -> type[BaseModel]:
        return TypedOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, TypeInput)
        task_id = require_task_context(context)
        data = await run_desktop(service().type_text(task_id, payload.text))
        return TypedOutput(**data)


class DesktopHotkeyTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return desktop_meta(
            name="tool.desktop.keyboard.hotkey",
            description="Press an allowlisted keyboard shortcut. Requires approval.",
            risk=ToolRisk.HIGH,
            input_schema="HotkeyInput",
            output_schema="HotkeyOutput",
            timeout_seconds=15.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return HotkeyInput

    @property
    def output_model(self) -> type[BaseModel]:
        return HotkeyOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, HotkeyInput)
        task_id = require_task_context(context)
        data = await run_desktop(service().hotkey(task_id, payload.keys))
        return HotkeyOutput(**data)


def all_desktop_tools() -> list[BaseTool]:
    return [
        DesktopScreenshotTool(),
        DesktopMousePositionTool(),
        DesktopDisplayInfoTool(),
        DesktopActiveWindowTool(),
        DesktopWaitTool(),
        DesktopMoveMouseTool(),
        DesktopClickTool(),
        DesktopDoubleClickTool(),
        DesktopScrollTool(),
        DesktopTypeTool(),
        DesktopHotkeyTool(),
    ]