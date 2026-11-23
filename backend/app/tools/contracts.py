from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.auth.permissions import Permission


class ToolRisk(StrEnum):
    LOW = "low"
    HIGH = "high"


class ToolContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    user_id: UUID | None = None
    permissions: frozenset[Permission] = Field(default_factory=frozenset)
    confirmed: bool = False


class ToolMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=20, pattern=r"^\d+\.\d+\.\d+$")
    description: str = Field(min_length=1, max_length=400)
    risk: ToolRisk
    required_permissions: list[Permission] = Field(default_factory=list)
    timeout_seconds: float = Field(default=5.0, gt=0, le=120)
    input_schema: str
    output_schema: str
    available: bool = True


class ToolSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    description: str
    risk: ToolRisk
    available: bool = True


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    output: str
    error_code: str | None = None
    data: dict[str, Any] | None = None


class Tool(Protocol):
    @property
    def metadata(self) -> ToolMetadata: ...

    async def validate(self, arguments: Mapping[str, Any]) -> None: ...

    async def execute(self, arguments: Mapping[str, Any], context: ToolContext) -> ToolResult: ...