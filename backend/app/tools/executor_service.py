import asyncio
import logging
import uuid
from collections.abc import Mapping
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.events.schemas import TaskEventType
from app.events.service import publish_task_event
from app.core.errors import UnknownToolError
from app.tools.base import BaseTool
from app.tools.contracts import Tool, ToolContext, ToolMetadata, ToolResult, ToolRisk
from app.safety.audit import log_tool_call
from app.safety.gateway import enforce_tool_safety
from app.tools.errors import ToolError, ToolPermissionError, ToolTimeoutError
from app.tools.registry import ToolRegistry

logger = logging.getLogger("app.tools.executor")


def _metadata(tool: Tool) -> ToolMetadata:
    if isinstance(tool, BaseTool):
        return tool.metadata
    name = getattr(tool, "name", "")
    return ToolMetadata(
        name=name,
        version=getattr(tool, "version", "0.0.0"),
        description=getattr(tool, "description", ""),
        risk=getattr(tool, "risk", ToolRisk.LOW),
        required_permissions=list(getattr(tool, "required_permissions", [])),
        timeout_seconds=float(getattr(tool, "timeout_seconds", get_settings().tool_default_timeout_seconds)),
        input_schema=getattr(tool, "input_schema", "unknown"),
        output_schema=getattr(tool, "output_schema", "unknown"),
        available=getattr(tool, "available", True),
    )


class ToolExecutorService:
    """Controlled execution entry point for registered tools."""

    name = "tools"
    detail = (
        "Safe tool framework is enabled. Shell, arbitrary Python, unrestricted filesystem "
        "access, and unbounded code execution are not exposed."
    )

    def availability(self) -> Literal["available"]:
        return "available"

    async def execute(
        self,
        name: str,
        arguments: Mapping[str, Any],
        context: ToolContext,
        registry: ToolRegistry,
        *,
        session: AsyncSession | None = None,
        agent_execution_id: uuid.UUID | None = None,
        step_sequence: int | None = None,
    ) -> ToolResult:
        try:
            tool = registry.get(name)
        except UnknownToolError:
            logger.warning(
                "tool_unknown",
                extra={"tool_name": name, "task_id": str(context.task_id), "user_id": str(context.user_id)},
            )
            raise

        metadata = _metadata(tool)
        if not metadata.available:
            return ToolResult(
                success=False,
                output=f"Tool '{name}' is not available.",
                error_code="tool_unavailable",
            )

        logger.info(
            "tool_execute_start",
            extra={
                "tool_name": name,
                "tool_version": metadata.version,
                "task_id": str(context.task_id),
                "user_id": str(context.user_id),
            },
        )

        if session is not None:
            await publish_task_event(
                session,
                user_id=context.user_id,
                task_id=context.task_id,
                event_type=TaskEventType.TOOL_STARTED,
                payload={
                    "tool_name": name,
                    "step_sequence": step_sequence,
                },
                agent_execution_id=agent_execution_id,
            )

        timeout = metadata.timeout_seconds or get_settings().tool_default_timeout_seconds
        try:
            await enforce_tool_safety(session, metadata=metadata, context=context, arguments=arguments)
            await tool.validate(arguments)
            result = await asyncio.wait_for(tool.execute(arguments, context), timeout=timeout)
        except asyncio.TimeoutError as exc:
            message = f"Tool '{name}' exceeded the {timeout}s timeout."
            logger.warning(
                "tool_execute_timeout",
                extra={"tool_name": name, "task_id": str(context.task_id), "timeout_seconds": timeout},
            )
            if session is not None:
                await publish_task_event(
                    session,
                    user_id=context.user_id,
                    task_id=context.task_id,
                    event_type=TaskEventType.TOOL_FAILED,
                    payload={
                        "tool_name": name,
                        "step_sequence": step_sequence,
                        "outcome_status": ToolTimeoutError.code,
                        "message": message[:500],
                    },
                    agent_execution_id=agent_execution_id,
                )
            return ToolResult(success=False, output=message, error_code=ToolTimeoutError.code)
        except ToolPermissionError as exc:
            logger.info(
                "tool_execute_blocked",
                extra={
                    "tool_name": name,
                    "task_id": str(context.task_id),
                    "error_code": exc.code,
                },
            )
            if session is not None:
                await log_tool_call(
                    session,
                    user_id=context.user_id,
                    task_id=context.task_id,
                    tool_name=name,
                    success=False,
                    error_code=exc.code,
                )
                await publish_task_event(
                    session,
                    user_id=context.user_id,
                    task_id=context.task_id,
                    event_type=TaskEventType.TOOL_FAILED,
                    payload={
                        "tool_name": name,
                        "step_sequence": step_sequence,
                        "outcome_status": exc.code,
                        "message": exc.message[:500],
                    },
                    agent_execution_id=agent_execution_id,
                )
            return ToolResult(success=False, output=exc.message, error_code=exc.code)
        except ToolError as exc:
            logger.info(
                "tool_execute_failed",
                extra={
                    "tool_name": name,
                    "task_id": str(context.task_id),
                    "error_code": exc.code,
                },
            )
            if session is not None:
                await log_tool_call(
                    session,
                    user_id=context.user_id,
                    task_id=context.task_id,
                    tool_name=name,
                    success=False,
                    error_code=exc.code,
                )
                await publish_task_event(
                    session,
                    user_id=context.user_id,
                    task_id=context.task_id,
                    event_type=TaskEventType.TOOL_FAILED,
                    payload={
                        "tool_name": name,
                        "step_sequence": step_sequence,
                        "outcome_status": exc.code,
                        "message": exc.message[:500],
                    },
                    agent_execution_id=agent_execution_id,
                )
            return ToolResult(success=False, output=exc.message, error_code=exc.code)
        except Exception as exc:
            logger.exception(
                "tool_execute_error",
                extra={"tool_name": name, "task_id": str(context.task_id)},
            )
            if session is not None:
                await publish_task_event(
                    session,
                    user_id=context.user_id,
                    task_id=context.task_id,
                    event_type=TaskEventType.TOOL_FAILED,
                    payload={
                        "tool_name": name,
                        "step_sequence": step_sequence,
                        "outcome_status": "tool_execution_error",
                        "message": str(exc)[:500],
                    },
                    agent_execution_id=agent_execution_id,
                )
            return ToolResult(success=False, output=str(exc), error_code="tool_execution_error")

        if not result.success:
            logger.info(
                "tool_execute_failed",
                extra={"tool_name": name, "task_id": str(context.task_id), "error_code": result.error_code},
            )
            if session is not None:
                await publish_task_event(
                    session,
                    user_id=context.user_id,
                    task_id=context.task_id,
                    event_type=TaskEventType.TOOL_FAILED,
                    payload={
                        "tool_name": name,
                        "step_sequence": step_sequence,
                        "outcome_status": result.error_code or "failed",
                        "message": (result.output or "")[:500],
                    },
                    agent_execution_id=agent_execution_id,
                )
        else:
            logger.info(
                "tool_execute_success",
                extra={"tool_name": name, "task_id": str(context.task_id)},
            )
            if session is not None:
                await log_tool_call(
                    session,
                    user_id=context.user_id,
                    task_id=context.task_id,
                    tool_name=name,
                    success=True,
                )
                await publish_task_event(
                    session,
                    user_id=context.user_id,
                    task_id=context.task_id,
                    event_type=TaskEventType.TOOL_COMPLETED,
                    payload={
                        "tool_name": name,
                        "step_sequence": step_sequence,
                        "outcome_status": "succeeded",
                        "message": (result.output or "")[:500],
                    },
                    agent_execution_id=agent_execution_id,
                )
        return result