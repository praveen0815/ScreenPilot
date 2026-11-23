from uuid import UUID

from app.auth.permissions import Permission
from app.automation.browser.errors import BrowserAutomationError
from app.automation.browser.playwright_service import get_browser_automation_service
from app.core.config import get_settings
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk
from app.tools.errors import ToolValidationError


def browser_available() -> bool:
    return bool(get_settings().browser_enabled)


def require_browser_user(context: ToolContext) -> tuple[UUID, UUID]:
    if context.user_id is None:
        raise ToolValidationError("Browser tools require an authenticated user context.")
    return context.user_id, context.task_id


def map_browser_error(exc: BrowserAutomationError) -> ToolValidationError:
    return ToolValidationError(exc.message)


async def run_browser(coro):
    try:
        return await coro
    except BrowserAutomationError as exc:
        raise map_browser_error(exc) from exc


def browser_meta(
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
        available=browser_available(),
    )


def service():
    return get_browser_automation_service()