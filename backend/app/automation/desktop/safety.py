import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from app.automation.desktop.errors import DesktopActionCancelledError, DesktopEmergencyStopError

logger = logging.getLogger("app.desktop.safety")


@dataclass
class DesktopActionRecord:
    action: str
    task_id: str
    success: bool
    detail: str
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DesktopSafetyGate:
    """Emergency stop and per-task cancellation. No background automation."""

    def __init__(self) -> None:
        self._emergency_stop = False
        self._cancelled_tasks: set[UUID] = set()
        self.action_log: list[DesktopActionRecord] = []

    @property
    def emergency_stop_active(self) -> bool:
        return self._emergency_stop

    def activate_emergency_stop(self) -> None:
        self._emergency_stop = True
        logger.warning("desktop_emergency_stop_activated")

    def clear_emergency_stop(self) -> None:
        self._emergency_stop = False
        logger.info("desktop_emergency_stop_cleared")

    def cancel_task(self, task_id: UUID) -> None:
        self._cancelled_tasks.add(task_id)
        logger.info("desktop_task_cancelled", extra={"task_id": str(task_id)})

    def clear_task_cancellation(self, task_id: UUID) -> None:
        self._cancelled_tasks.discard(task_id)

    def assert_allowed(self, task_id: UUID) -> None:
        if self._emergency_stop:
            raise DesktopEmergencyStopError("Desktop emergency stop is active.")
        if task_id in self._cancelled_tasks:
            raise DesktopActionCancelledError("Desktop actions are cancelled for this task.")

    def record(self, *, action: str, task_id: UUID, success: bool, detail: str) -> None:
        entry = DesktopActionRecord(
            action=action,
            task_id=str(task_id),
            success=success,
            detail=detail[:300],
        )
        self.action_log.append(entry)
        logger.info(
            "desktop_action",
            extra={
                "action": action,
                "task_id": str(task_id),
                "success": success,
                "detail": entry.detail,
            },
        )


_gate = DesktopSafetyGate()


def get_desktop_safety_gate() -> DesktopSafetyGate:
    return _gate