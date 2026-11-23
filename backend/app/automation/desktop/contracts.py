"""Desktop automation command contract (Phase 1 compatibility)."""

import re
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.errors import AutomationUnavailableError

_KEY = re.compile(r"^[A-Za-z0-9_+]{1,20}$")


class DesktopAction(StrEnum):
    MOVE = "move"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"


class DesktopCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: DesktopAction
    x: int | None = Field(default=None, ge=0, le=20000)
    y: int | None = Field(default=None, ge=0, le=20000)
    text: str | None = Field(default=None, max_length=2000)
    keys: list[str] | None = None
    delta_y: int | None = Field(default=None, ge=-5000, le=5000)

    @model_validator(mode="after")
    def required_fields(self) -> Self:
        if self.action is DesktopAction.MOVE and (self.x is None or self.y is None):
            raise ValueError("move requires x and y")
        if self.action is DesktopAction.CLICK and (self.x is None or self.y is None):
            raise ValueError("click requires x and y")
        if self.action is DesktopAction.TYPE_TEXT and not self.text:
            raise ValueError("type_text requires text")
        if self.action is DesktopAction.SCROLL and self.delta_y is None:
            raise ValueError("scroll requires delta_y")
        if self.action is DesktopAction.HOTKEY:
            if not self.keys:
                raise ValueError("hotkey requires keys")
            if any(_KEY.fullmatch(key) is None for key in self.keys):
                raise ValueError("hotkey keys contain unsupported characters")
        return self


class DesktopObservation(BaseModel):
    success: bool
    detail: str


class DesktopAutomationUnavailable:
    name = "desktop"
    detail = "Desktop automation is not enabled in this build."

    def availability(self) -> Literal["unavailable"]:
        return "unavailable"

    async def execute(self, command: DesktopCommand) -> DesktopObservation:
        del command
        raise AutomationUnavailableError("desktop")