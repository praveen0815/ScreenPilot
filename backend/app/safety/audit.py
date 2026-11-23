import json
import logging
import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog
from app.memory.sanitize import MemoryPolicyError, sanitize_text_for_memory

logger = logging.getLogger("app.safety.audit")

_SECRET_PATTERN = re.compile(r"(password|token|secret|credential|api[_-]?key|bearer)", re.I)


def _safe_metadata(payload: dict) -> str:
    cleaned: dict = {}
    for key, value in payload.items():
        if _SECRET_PATTERN.search(str(key)) or _SECRET_PATTERN.search(str(value)):
            cleaned[str(key)] = "[redacted]"
        else:
            cleaned[str(key)] = str(value)[:300]
    return json.dumps(cleaned)


async def log_safety_event(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    task_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    row = AuditLog(
        user_id=user_id,
        task_id=task_id,
        action=action[:120],
        resource_type=resource_type[:80],
        resource_id=resource_id[:80] if resource_id else None,
        metadata_json=_safe_metadata(metadata or {}),
    )
    session.add(row)
    await session.flush()
    logger.info(
        "safety_audit",
        extra={
            "action": action,
            "resource_type": resource_type,
            "task_id": str(task_id) if task_id else None,
            "user_id": str(user_id) if user_id else None,
        },
    )


async def log_tool_call(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    task_id: UUID | None,
    tool_name: str,
    success: bool,
    error_code: str | None = None,
) -> None:
    await log_safety_event(
        session,
        user_id=user_id,
        task_id=task_id,
        action="tool_call" if success else "tool_call_failed",
        resource_type="tool",
        resource_id=tool_name,
        metadata={"success": success, "error_code": error_code or ""},
    )


async def log_blocked_action(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    task_id: UUID | None,
    tool_name: str,
    reason: str,
) -> None:
    try:
        safe_reason = sanitize_text_for_memory(reason, max_chars=500)
    except MemoryPolicyError:
        safe_reason = "blocked-reason-redacted"
    await log_safety_event(
        session,
        user_id=user_id,
        task_id=task_id,
        action="action_blocked",
        resource_type="tool",
        resource_id=tool_name,
        metadata={"reason": safe_reason},
    )


async def log_approval_decision(
    session: AsyncSession,
    *,
    user_id: UUID,
    task_id: UUID,
    approval_id: UUID,
    decision: str,
) -> None:
    await log_safety_event(
        session,
        user_id=user_id,
        task_id=task_id,
        action=f"approval_{decision}",
        resource_type="approval",
        resource_id=str(approval_id),
        metadata={},
    )