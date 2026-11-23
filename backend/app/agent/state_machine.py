from app.core.errors import AppError
from app.db.enums import TaskStatus

TERMINAL_STATUSES = frozenset(
    {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
)

ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset(
        {TaskStatus.PLANNING, TaskStatus.CANCELLED, TaskStatus.FAILED}
    ),
    TaskStatus.PLANNING: frozenset(
        {TaskStatus.AWAITING_APPROVAL, TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED}
    ),
    TaskStatus.AWAITING_APPROVAL: frozenset(
        {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED, TaskStatus.PAUSED}
    ),
    TaskStatus.PAUSED: frozenset(
        {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED}
    ),
    TaskStatus.RUNNING: frozenset(
        {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.PAUSED}
    ),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.FAILED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


def transition(current: TaskStatus, target: TaskStatus) -> None:
    if current in TERMINAL_STATUSES:
        raise AppError(
            code="invalid_transition",
            message=f"Task in terminal state '{current.value}' cannot move to '{target.value}'.",
            status_code=409,
        )
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise AppError(
            code="invalid_transition",
            message=f"Cannot transition from '{current.value}' to '{target.value}'.",
            status_code=409,
        )