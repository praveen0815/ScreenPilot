"""Contracts for the future agent runtime.

Phase 1 defines the data the runtime will accept and return.
It does not plan, call tools, or invoke a model.
"""

from typing import Protocol

from app.schemas.agent import AgentOutcome, AgentTask


class AgentRuntime(Protocol):
    name: str
    detail: str

    def availability(self) -> str: ...

    async def run(self, task: AgentTask, *, session, user) -> AgentOutcome: ...  # type: ignore[no-untyped-def]
