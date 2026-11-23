from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayInfo:
    width: int
    height: int


@dataclass(frozen=True)
class MousePosition:
    x: int
    y: int


class DesktopAdapter(ABC):
    """Controlled desktop surface — no arbitrary PyAutoGUI passthrough."""

    name: str

    @abstractmethod
    def display_info(self) -> DisplayInfo: ...

    @abstractmethod
    def mouse_position(self) -> MousePosition: ...

    @abstractmethod
    def move_mouse(self, x: int, y: int) -> None: ...

    @abstractmethod
    def click(self, x: int, y: int, *, button: str = "left") -> None: ...

    @abstractmethod
    def double_click(self, x: int, y: int) -> None: ...

    @abstractmethod
    def scroll(self, delta_y: int) -> None: ...

    @abstractmethod
    def type_text(self, text: str) -> None: ...

    @abstractmethod
    def hotkey(self, keys: tuple[str, ...]) -> None: ...

    @abstractmethod
    def screenshot_png(self) -> bytes: ...

    @abstractmethod
    def active_window_title(self) -> tuple[bool, str | None]: ...