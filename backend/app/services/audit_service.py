import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    resource_type: str,
    user_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        task_id=task_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    session.add(entry)
    await session.flush()
    return entry