from app.core.errors import UnknownToolError
from app.tools.base import BaseTool
from app.tools.contracts import Tool, ToolMetadata, ToolSpec


class ToolRegistry:
    """In-memory tool catalog with versioned metadata."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = tool.metadata.name if isinstance(tool, BaseTool) else getattr(tool, "name")
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise UnknownToolError(name) from exc

    def allowed_tool_names(self) -> frozenset[str]:
        return frozenset(self._tools.keys())

    def list_metadata(self) -> list[ToolMetadata]:
        items: list[ToolMetadata] = []
        for tool in self._tools.values():
            if isinstance(tool, BaseTool):
                items.append(tool.metadata)
            else:
                items.append(
                    ToolMetadata(
                        name=tool.name,
                        version=getattr(tool, "version", "0.0.0"),
                        description=tool.description,
                        risk=tool.risk,
                        required_permissions=list(getattr(tool, "required_permissions", [])),
                        timeout_seconds=float(getattr(tool, "timeout_seconds", 5.0)),
                        input_schema=getattr(tool, "input_schema", "unknown"),
                        output_schema=getattr(tool, "output_schema", "unknown"),
                        available=getattr(tool, "available", True),
                    )
                )
        return sorted(items, key=lambda row: row.name)

    def list_specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name=item.name,
                version=item.version,
                description=item.description,
                risk=item.risk,
                available=item.available,
            )
            for item in self.list_metadata()
        ]


_REGISTERED_TOOL_COUNT = 0


def registered_tool_count() -> int:
    return _REGISTERED_TOOL_COUNT


def build_registry() -> ToolRegistry:
    global _REGISTERED_TOOL_COUNT
    from app.tools.mock_impl import MockObserveTool, MockSummarizeTool
    from app.tools.mock_workflow import MockWorkflowAttemptTool
    from app.tools.safe.app_status import AppStatusAdminTool, AppStatusTool
    from app.tools.safe.calculator import CalculatorTool
    from app.tools.safe.current_time import CurrentTimeTool
    from app.tools.safe.text_transform import TextTransformTool
    from app.tools.browser import all_browser_tools
    from app.tools.desktop import all_desktop_tools
    from app.tools.vision import all_vision_tools

    registry = ToolRegistry()
    for tool in (
        CurrentTimeTool(),
        CalculatorTool(),
        AppStatusTool(),
        AppStatusAdminTool(),
        TextTransformTool(),
        MockObserveTool(),
        MockSummarizeTool(),
        MockWorkflowAttemptTool(),
        *all_browser_tools(),
        *all_desktop_tools(),
        *all_vision_tools(),
    ):
        registry.register(tool)
    _REGISTERED_TOOL_COUNT = len(registry._tools)
    return registry