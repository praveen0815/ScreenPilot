import asyncio
from functools import partial

from app.automation.desktop.adapter import DesktopAdapter, DisplayInfo, MousePosition
from app.automation.desktop.errors import DesktopActionError


class PyAutoGUIDesktopAdapter(DesktopAdapter):
    name = "pyautogui"

    def __init__(self) -> None:
        import pyautogui

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        self._pyautogui = pyautogui

    def display_info(self) -> DisplayInfo:
        size = self._pyautogui.size()
        return DisplayInfo(width=int(size.width), height=int(size.height))

    def mouse_position(self) -> MousePosition:
        pos = self._pyautogui.position()
        return MousePosition(x=int(pos.x), y=int(pos.y))

    def move_mouse(self, x: int, y: int) -> None:
        self._pyautogui.moveTo(x, y)

    def click(self, x: int, y: int, *, button: str = "left") -> None:
        if button not in {"left", "right", "middle"}:
            raise DesktopActionError("Unsupported mouse button.")
        self._pyautogui.click(x=x, y=y, button=button)

    def double_click(self, x: int, y: int) -> None:
        self._pyautogui.doubleClick(x=x, y=y)

    def scroll(self, delta_y: int) -> None:
        clicks = int(delta_y / 100) if delta_y else 0
        if clicks == 0:
            clicks = 1 if delta_y > 0 else -1
        self._pyautogui.scroll(clicks)

    def type_text(self, text: str) -> None:
        self._pyautogui.write(text, interval=0.02)

    def hotkey(self, keys: tuple[str, ...]) -> None:
        self._pyautogui.hotkey(*keys)

    def screenshot_png(self) -> bytes:
        image = self._pyautogui.screenshot()
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def active_window_title(self) -> tuple[bool, str | None]:
        try:
            import pygetwindow

            window = pygetwindow.getActiveWindow()
            if window is None:
                return True, None
            return True, (window.title or "")[:500]
        except Exception:
            return False, None


async def run_adapter_call(func, *args, timeout: float):
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(loop.run_in_executor(None, partial(func, *args)), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise DesktopActionError("Desktop adapter call timed out.") from exc