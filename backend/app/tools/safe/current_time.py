from datetime import datetime, timezone

from pydantic import BaseModel

from app.auth.permissions import Permission
from app.tools.base import BaseTool
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk
from app.tools.safe.schemas import CurrentTimeInput, CurrentTimeOutput


class CurrentTimeTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="tool.current_time",
            version="1.0.0",
            description="Return the current UTC timestamp.",
            risk=ToolRisk.LOW,
            required_permissions=[Permission.TASK_WRITE],
            timeout_seconds=2.0,
            input_schema="CurrentTimeInput",
            output_schema="CurrentTimeOutput",
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return CurrentTimeInput

    @property
    def output_model(self) -> type[BaseModel]:
        return CurrentTimeOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del payload, context
        return CurrentTimeOutput(iso_utc=datetime.now(timezone.utc).isoformat())