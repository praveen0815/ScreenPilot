from app.agent.schemas.plan import TaskPlan
from app.db.enums import StepStatus
from app.db.models.task_step import TaskStep
from app.workflow.schemas import WorkflowState


class WorkflowCompletionError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _coerce_step_status(value: StepStatus | str) -> StepStatus:
    if isinstance(value, StepStatus):
        return value
    return StepStatus(value)


def validate_workflow_completion(
    plan: TaskPlan,
    *,
    steps: list[TaskStep],
    state: WorkflowState,
) -> None:
    by_seq = {row.sequence: row for row in steps}
    for spec in plan.steps:
        row = by_seq.get(spec.sequence)
        if row is None:
            raise WorkflowCompletionError(f"Missing persisted step {spec.sequence}.")
        status = _coerce_step_status(row.status)
        if status is StepStatus.SKIPPED:
            continue
        if status is not StepStatus.COMPLETED:
            raise WorkflowCompletionError(f"Step {spec.sequence} did not finish.")
    if state.last_sequence < max(spec.sequence for spec in plan.steps):
        raise WorkflowCompletionError("Workflow cursor did not reach the final step.")