from pydantic import BaseModel

from app import __version__
from app.auth.permissions import Permission
from app.core.config import get_settings
from app.tools.base import BaseTool
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk
from app.tools.registry import registered_tool_count
from app.tools.safe.schemas import AppStatusInput, AppStatusOutput


class AppStatusTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="tool.app_status",
            version="1.0.0",
            description="Read ScreenPilot application status from configuration.",
            risk=ToolRisk.LOW,
            required_permissions=[Permission.TASK_READ],
            timeout_seconds=3.0,
            input_schema="AppStatusInput",
            output_schema="AppStatusOutput",
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return AppStatusInput

    @property
    def output_model(self) -> type[BaseModel]:
        return AppStatusOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del payload, context
        settings = get_settings()
        return AppStatusOutput(
            service=settings.app_name,
            version=__version__,
            llm_provider=settings.llm_provider,
            tools_available=registered_tool_count(),
        )


class AppStatusAdminTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="tool.app_status.admin",
            version="1.0.0",
            description="Admin-only application status introspection.",
            risk=ToolRisk.LOW,
            required_permissions=[Permission.ADMIN_ALL],
            timeout_seconds=3.0,
            input_schema="AppStatusInput",
            output_schema="AppStatusOutput",
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return AppStatusInput

    @property
    def output_model(self) -> type[BaseModel]:
        return AppStatusOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del payload, context
        settings = get_settings()
        return AppStatusOutput(
            service=settings.app_name,
            version=__version__,
            llm_provider=settings.llm_provider,
            tools_available=-1,
        )