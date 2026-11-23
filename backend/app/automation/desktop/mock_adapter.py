import base64
from dataclasses import dataclass, field

from app.automation.desktop.adapter import DesktopAdapter, DisplayInfo, MousePosition


def _tiny_png() -> bytes:
    # 1x1 transparent PNG
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


@dataclass
class MockDesktopAdapter(DesktopAdapter):
    name: str = "mock"

    width: int = 1920
    height: int = 1080
    mouse_x: int = 100
    mouse_y: int = 100
    calls: list[str] = field(default_factory=list)

    def display_info(self) -> DisplayInfo:
        return DisplayInfo(width=self.width, height=self.height)

    def mouse_position(self) -> MousePosition:
        return MousePosition(x=self.mouse_x, y=self.mouse_y)

    def move_mouse(self, x: int, y: int) -> None:
        self.calls.append(f"move:{x},{y}")
        self.mouse_x, self.mouse_y = x, y

    def click(self, x: int, y: int, *, button: str = "left") -> None:
        self.calls.append(f"click:{button}:{x},{y}")
        self.mouse_x, self.mouse_y = x, y

    def double_click(self, x: int, y: int) -> None:
        self.calls.append(f"double_click:{x},{y}")
        self.mouse_x, self.mouse_y = x, y

    def scroll(self, delta_y: int) -> None:
        self.calls.append(f"scroll:{delta_y}")

    def type_text(self, text: str) -> None:
        self.calls.append(f"type:{text[:32]}")

    def hotkey(self, keys: tuple[str, ...]) -> None:
        self.calls.append(f"hotkey:{'+'.join(keys)}")

    def screenshot_png(self) -> bytes:
        self.calls.append("screenshot")
        return _tiny_png()

    def active_window_title(self) -> tuple[bool, str | None]:
        return True, "Mock Active Window"