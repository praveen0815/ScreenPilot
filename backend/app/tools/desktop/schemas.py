from pydantic import BaseModel, ConfigDict, Field


class PointInput(BaseModel):
    x: int = Field(ge=0, le=20000)
    y: int = Field(ge=0, le=20000)


class ClickInput(PointInput):
    button: str = Field(default="left", pattern=r"^(left|right|middle)$")


class DoubleClickInput(PointInput):
    pass


class ScrollInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delta_y: int = Field(ge=-5000, le=5000)


class TypeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=500)


class HotkeyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keys: list[str] = Field(min_length=1, max_length=6)


class WaitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    milliseconds: int = Field(ge=50, le=60000)


class ScreenshotOutput(BaseModel):
    image_base64: str
    byte_length: int
    format: str


class PositionOutput(BaseModel):
    x: int
    y: int


class DisplayOutput(BaseModel):
    width: int
    height: int


class WindowOutput(BaseModel):
    supported: bool
    title: str | None


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TypedOutput(BaseModel):
    typed: bool


class HotkeyOutput(BaseModel):
    keys: list[str]


class WaitOutput(BaseModel):
    completed: bool


class ClickOutput(BaseModel):
    x: int
    y: int
    button: str


class ScrollOutput(BaseModel):
    delta_y: int


class MoveOutput(BaseModel):
    x: int
    y: int