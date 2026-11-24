from app.agent.schemas.plan import PlanStepSpec
from app.workflow.schemas import WorkflowRunWhen, WorkflowState


def should_run_step(
    spec: PlanStepSpec,
    *,
    state: WorkflowState,
) -> bool:
    when = spec.run_when
    if when == WorkflowRunWhen.ALWAYS:
        return True
    if when == WorkflowRunWhen.ON_PREV_SUCCESS:
        return state.last_success is True
    if when == WorkflowRunWhen.ON_PREV_FAILURE:
        return state.last_success is False
    return True