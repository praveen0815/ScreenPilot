from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BrowserSessionRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID


class SessionCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionCreateOutput(BaseModel):
    session_id: UUID


class SessionCloseInput(BrowserSessionRef):
    pass


class SessionCloseOutput(BaseModel):
    actions_recorded: int


class NavigateInput(BrowserSessionRef):
    url: str = Field(min_length=1, max_length=2000)


class NavigateOutput(BaseModel):
    url: str
    title: str


class TitleInput(BrowserSessionRef):
    pass


class TitleOutput(BaseModel):
    title: str


class TextInput(BrowserSessionRef):
    pass


class TextOutput(BaseModel):
    text: str


class ScreenshotInput(BrowserSessionRef):
    pass


class ScreenshotOutput(BaseModel):
    image_base64: str
    byte_length: int
    format: str


class InspectInput(BrowserSessionRef):
    selector: str = Field(min_length=1, max_length=500)


class InspectOutput(BaseModel):
    selector: str
    tag: str
    text: str
    visible: bool
    height: int | None
    width: int | None


class ClickInput(BrowserSessionRef):
    selector: str = Field(min_length=1, max_length=500)


class ClickOutput(BaseModel):
    url: str


class TypeInput(BrowserSessionRef):
    selector: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1, max_length=2000)
    clear_first: bool = True


class TypeOutput(BaseModel):
    typed: bool


class ScrollInput(BrowserSessionRef):
    delta_y: int = Field(default=0, ge=-5000, le=5000)
    selector: str | None = Field(default=None, max_length=500)


class ScrollOutput(BaseModel):
    scrolled: bool


class WaitState(StrEnum):
    ATTACHED = "attached"
    DETACHED = "detached"
    VISIBLE = "visible"
    HIDDEN = "hidden"


class WaitInput(BrowserSessionRef):
    selector: str = Field(min_length=1, max_length=500)
    state: WaitState = WaitState.VISIBLE
    timeout_ms: int = Field(default=5000, ge=100, le=60000)


class WaitOutput(BaseModel):
    ready: bool


class FormField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selector: str = Field(min_length=1, max_length=500)
    value: str = Field(min_length=0, max_length=2000)


class FormFillInput(BrowserSessionRef):
    fields: list[FormField] = Field(min_length=1, max_length=20)


class FormFillOutput(BaseModel):
    fields_filled: int


class FormSubmitInput(BrowserSessionRef):
    selector: str = Field(min_length=1, max_length=500)


class FormSubmitOutput(BaseModel):
    url: str