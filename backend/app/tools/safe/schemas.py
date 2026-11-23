from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TextTransformOp(StrEnum):
    UPPER = "upper"
    LOWER = "lower"
    TRIM = "trim"
    SLUG = "slug"


class CurrentTimeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CurrentTimeOutput(BaseModel):
    iso_utc: str


class CalculatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expression: str = Field(min_length=1, max_length=120)


class CalculatorOutput(BaseModel):
    value: float


class AppStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppStatusOutput(BaseModel):
    service: str
    version: str
    llm_provider: str
    tools_available: int


class TextTransformInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: TextTransformOp
    text: str = Field(min_length=1, max_length=4000)


class TextTransformOutput(BaseModel):
    result: str