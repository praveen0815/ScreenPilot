"""Browser automation command contract (validated arguments; no direct Playwright exposure)."""

import re
from enum import StrEnum
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.errors import AutomationUnavailableError

_KEY = re.compile(r"^[A-Za-z0-9_+]{1,20}$")


class BrowserAction(StrEnum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    SCROLL = "scroll"
    SNAPSHOT = "snapshot"


class BrowserCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: BrowserAction
    url: str | None = None
    selector: str | None = Field(default=None, max_length=500)
    text: str | None = Field(default=None, max_length=2000)
    key: str | None = None
    delta_y: int | None = Field(default=None, ge=-5000, le=5000)

    @model_validator(mode="after")
    def required_fields(self) -> Self:
        required: dict[BrowserAction, tuple[str, ...]] = {
            BrowserAction.NAVIGATE: ("url",),
            BrowserAction.CLICK: ("selector",),
            BrowserAction.TYPE_TEXT: ("selector", "text"),
            BrowserAction.PRESS_KEY: ("key",),
            BrowserAction.SCROLL: ("delta_y",),
            BrowserAction.SNAPSHOT: (),
        }
        missing = [field for field in required[self.action] if getattr(self, field) in (None, "")]
        if missing:
            raise ValueError(f"{self.action.value} requires {', '.join(missing)}")
        if self.action is BrowserAction.NAVIGATE and self.url is not None:
            parsed = urlparse(self.url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("navigate url must be an absolute http(s) URL")
        if self.key is not None and _KEY.fullmatch(self.key) is None:
            raise ValueError("key contains unsupported characters")
        return self


class BrowserObservation(BaseModel):
    success: bool
    detail: str
    url: str | None = None


class BrowserAutomationUnavailable:
    name = "browser"
    detail = "Browser automation is not enabled in this build."

    def availability(self) -> Literal["unavailable"]:
        return "unavailable"

    async def execute(self, command: BrowserCommand) -> BrowserObservation:
        del command
        raise AutomationUnavailableError("browser")