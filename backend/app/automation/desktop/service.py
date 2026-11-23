import asyncio
import base64
import logging
from functools import partial
from uuid import UUID

from app.automation.desktop.adapter import DesktopAdapter
from app.automation.desktop.errors import (
    DesktopActionError,
    DesktopBoundsError,
    DesktopDisabledError,
)
from app.automation.desktop.hotkeys import validate_hotkey
from app.automation.desktop.mock_adapter import MockDesktopAdapter
from app.automation.desktop.safety import get_desktop_safety_gate
from app.core.config import Settings, get_settings

logger = logging.getLogger("app.desktop.service")

_adapter: DesktopAdapter | None = None


def _build_adapter(settings: Settings) -> DesktopAdapter:
    if settings.desktop_adapter == "mock":
        return MockDesktopAdapter()
    if settings.desktop_adapter == "pyautogui":
        from app.automation.desktop.pyautogui_adapter import PyAutoGUIDesktopAdapter

        return PyAutoGUIDesktopAdapter()
    raise DesktopDisabledError("Unknown desktop adapter.")


def get_desktop_adapter() -> DesktopAdapter:
    global _adapter
    settings = get_settings()
    if _adapter is None:
        _adapter = _build_adapter(settings)
    return _adapter


def reset_desktop_adapter_for_tests() -> None:
    global _adapter
    _adapter = None


class DesktopAutomationService:
    name = "desktop"
    detail = "Controlled desktop automation via a validated adapter (mock or PyAutoGUI)."

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._gate = get_desktop_safety_gate()

    def availability(self) -> str:
        return "available" if self._settings.desktop_enabled else "unavailable"

    def _require_enabled(self) -> None:
        if not self._settings.desktop_enabled:
            raise DesktopDisabledError("Desktop automation is disabled.")

    def _bounds(self, adapter: DesktopAdapter) -> tuple[int, int]:
        info = adapter.display_info()
        return info.width, info.height

    def _validate_point(self, adapter: DesktopAdapter, x: int, y: int) -> None:
        width, height = self._bounds(adapter)
        if x < 0 or y < 0 or x >= width or y >= height:
            raise DesktopBoundsError(f"Coordinates ({x}, {y}) are outside the screen ({width}x{height}).")

    async def _run(self, task_id: UUID, action: str, func, *args):
        self._require_enabled()
        self._gate.assert_allowed(task_id)
        timeout = self._settings.desktop_action_timeout_seconds
        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, partial(func, *args)),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            self._gate.record(action=action, task_id=task_id, success=False, detail="timeout")
            raise DesktopActionError("Desktop action timed out.") from exc
        except Exception as exc:
            self._gate.record(action=action, task_id=task_id, success=False, detail=str(exc)[:200])
            if isinstance(exc, DesktopBoundsError):
                raise
            raise DesktopActionError("Desktop action failed.") from exc
        self._gate.record(action=action, task_id=task_id, success=True, detail="ok")
        return result

    async def screenshot(self, task_id: UUID) -> dict[str, str | int]:
        adapter = get_desktop_adapter()
        raw: bytes = await self._run(task_id, "screenshot", partial(adapter.screenshot_png))
        if len(raw) > self._settings.desktop_max_screenshot_bytes:
            raise DesktopActionError("Screenshot exceeds configured size limit.")
        return {
            "image_base64": base64.b64encode(raw).decode("ascii"),
            "byte_length": len(raw),
            "format": "png",
        }

    async def mouse_position(self, task_id: UUID) -> dict[str, int]:
        adapter = get_desktop_adapter()
        pos = await self._run(task_id, "mouse.position", partial(adapter.mouse_position))
        return {"x": pos.x, "y": pos.y}

    async def display_info(self, task_id: UUID) -> dict[str, int]:
        adapter = get_desktop_adapter()
        info = await self._run(task_id, "display.info", partial(adapter.display_info))
        return {"width": info.width, "height": info.height}

    async def active_window(self, task_id: UUID) -> dict[str, bool | str | None]:
        adapter = get_desktop_adapter()
        supported, title = await self._run(task_id, "window.active", partial(adapter.active_window_title))
        return {"supported": supported, "title": title}

    async def wait_ms(self, task_id: UUID, milliseconds: int) -> dict[str, bool]:
        self._require_enabled()
        capped = min(max(milliseconds, 50), self._settings.desktop_wait_max_ms)
        remaining = capped
        while remaining > 0:
            self._gate.assert_allowed(task_id)
            step = min(100, remaining)
            await asyncio.sleep(step / 1000)
            remaining -= step
        self._gate.record(action="wait", task_id=task_id, success=True, detail=f"{capped}ms")
        return {"completed": True}

    async def move_mouse(self, task_id: UUID, x: int, y: int) -> dict[str, int]:
        adapter = get_desktop_adapter()
        self._validate_point(adapter, x, y)
        await self._run(task_id, "mouse.move", partial(adapter.move_mouse, x, y))
        return {"x": x, "y": y}

    async def click(self, task_id: UUID, x: int, y: int, button: str = "left") -> dict[str, int | str]:
        adapter = get_desktop_adapter()
        self._validate_point(adapter, x, y)
        await self._run(task_id, "mouse.click", partial(adapter.click, x, y, button=button))
        return {"x": x, "y": y, "button": button}

    async def double_click(self, task_id: UUID, x: int, y: int) -> dict[str, int]:
        adapter = get_desktop_adapter()
        self._validate_point(adapter, x, y)
        await self._run(task_id, "mouse.double_click", partial(adapter.double_click, x, y))
        return {"x": x, "y": y}

    async def scroll(self, task_id: UUID, delta_y: int) -> dict[str, int]:
        adapter = get_desktop_adapter()
        await self._run(task_id, "scroll", partial(adapter.scroll, delta_y))
        return {"delta_y": delta_y}

    async def type_text(self, task_id: UUID, text: str) -> dict[str, bool]:
        if "\n" in text or "\r" in text:
            raise DesktopActionError("Newlines are not allowed in desktop typing.")
        adapter = get_desktop_adapter()
        await self._run(task_id, "keyboard.type", partial(adapter.type_text, text))
        return {"typed": True}

    async def hotkey(self, task_id: UUID, keys: list[str]) -> dict[str, list[str]]:
        normalized = validate_hotkey(keys)
        adapter = get_desktop_adapter()
        await self._run(task_id, "keyboard.hotkey", partial(adapter.hotkey, normalized))
        return {"keys": list(normalized)}


_service: DesktopAutomationService | None = None


def get_desktop_automation_service() -> DesktopAutomationService:
    global _service
    if _service is None:
        _service = DesktopAutomationService()
    return _service