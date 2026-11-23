from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.tools.contracts import ToolRisk
from app.tools.registry import build_registry


def registered_tool_names() -> frozenset[str]:
    return build_registry().allowed_tool_names()


class TaskIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=500)
    objective: str = Field(min_length=1, max_length=500)
    constraints: list[str] = Field(default_factory=list, max_length=10)


class PlanStepSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1, le=50)
    description: str = Field(min_length=1, max_length=500)
    tool_name: str = Field(min_length=1, max_length=120)
    arguments: dict[str, str | int | float | bool] = Field(default_factory=dict)
    risk: ToolRisk = ToolRisk.LOW

    @field_validator("tool_name")
    @classmethod
    def tool_must_be_registered(cls, value: str) -> str:
        if value not in registered_tool_names():
            raise ValueError(f"Tool '{value}' is not registered.")
        return value


class TaskPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=500)
    steps: list[PlanStepSpec] = Field(min_length=1, max_length=50)

    @field_validator("steps")
    @classmethod
    def steps_must_be_sequenced(cls, value: list[PlanStepSpec]) -> list[PlanStepSpec]:
        sequences = [step.sequence for step in value]
        if len(set(sequences)) != len(sequences):
            raise ValueError("Plan steps must have unique sequence numbers.")
        expected = list(range(1, len(value) + 1))
        if sorted(sequences) != expected:
            raise ValueError("Plan steps must be numbered contiguously from 1.")
        return value