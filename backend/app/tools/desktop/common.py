from uuid import UUID

from app.auth.permissions import Permission
from app.automation.desktop.errors import DesktopAutomationError
from app.automation.desktop.service import get_desktop_automation_service
from app.core.config import get_settings
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk
from app.tools.errors import ToolValidationError


def desktop_available() -> bool:
    return bool(get_settings().desktop_enabled)


def require_task_context(context: ToolContext) -> UUID:
    if context.user_id is None:
        raise ToolValidationError("Desktop tools require an authenticated user context.")
    return context.task_id


def map_desktop_error(exc: DesktopAutomationError) -> ToolValidationError:
    return ToolValidationError(exc.message)


async def run_desktop(coro):
    try:
        return await coro
    except DesktopAutomationError as exc:
        raise map_desktop_error(exc) from exc


def desktop_meta(
    *,
    name: str,
    description: str,
    risk: ToolRisk,
    input_schema: str,
    output_schema: str,
    timeout_seconds: float,
) -> ToolMetadata:
    return ToolMetadata(
        name=name,
        version="1.0.0",
        description=description,
        risk=risk,
        required_permissions=[Permission.TASK_WRITE],
        timeout_seconds=timeout_seconds,
        input_schema=input_schema,
        output_schema=output_schema,
        available=desktop_available(),
    )


def service():
    return get_desktop_automation_service()