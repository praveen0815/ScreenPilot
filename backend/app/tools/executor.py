from collections.abc import Mapping
from typing import Any, Literal

from app.core.errors import AutomationUnavailableError
from app.tools.contracts import ToolContext, ToolResult
from app.tools.registry import ToolRegistry


class ToolExecutor:
    """Execution gate for registered tools.

    The method accepts a registry so the future implementation has a stable
    signature. This build raises before looking up or calling a tool.
    """

    name = "tools"
    detail = "Tool execution is not enabled in this build."

    def availability(self) -> Literal["unavailable"]:
        return "unavailable"

    async def execute(
        self,
        name: str,
        arguments: Mapping[str, Any],
        context: ToolContext,
        registry: ToolRegistry,
    ) -> ToolResult:
        del name, arguments, context, registry
        raise AutomationUnavailableError("tool")
