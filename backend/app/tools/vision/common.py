from app.auth.permissions import Permission
from app.automation.vision.errors import VisionError
from app.automation.vision.service import get_screen_intelligence_service
from app.core.config import get_settings
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk
from app.tools.errors import ToolValidationError


def vision_available() -> bool:
    return bool(get_settings().vision_enabled)


def require_user(context: ToolContext) -> None:
    if context.user_id is None:
        raise ToolValidationError("Vision tools require an authenticated user context.")


def map_vision_error(exc: VisionError) -> ToolValidationError:
    return ToolValidationError(exc.message)


async def run_vision(coro):
    try:
        return await coro
    except VisionError as exc:
        raise map_vision_error(exc) from exc


def vision_meta(
    *,
    name: str,
    description: str,
    input_schema: str,
    output_schema: str,
    timeout_seconds: float,
) -> ToolMetadata:
    return ToolMetadata(
        name=name,
        version="1.0.0",
        description=description,
        risk=ToolRisk.LOW,
        required_permissions=[Permission.TASK_READ],
        timeout_seconds=timeout_seconds,
        input_schema=input_schema,
        output_schema=output_schema,
        available=vision_available(),
    )


def service():
    return get_screen_intelligence_service()