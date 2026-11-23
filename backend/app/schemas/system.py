from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str


class CheckResult(BaseModel):
    status: Literal["up", "down"]
    detail: str | None = None


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, CheckResult]


class CapabilityStatus(BaseModel):
    name: str
    state: Literal["unavailable", "mock", "available"]
    detail: str


class CapabilitiesResponse(BaseModel):
    capabilities: list[CapabilityStatus] = Field(default_factory=list)
