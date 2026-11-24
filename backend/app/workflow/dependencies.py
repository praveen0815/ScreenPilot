from app.agent.schemas.plan import PlanStepSpec, TaskPlan


class WorkflowDependencyError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def validate_step_dependencies(plan: TaskPlan) -> None:
    sequences = {step.sequence for step in plan.steps}
    for step in plan.steps:
        for dep in step.depends_on:
            if dep not in sequences:
                raise WorkflowDependencyError(f"Step {step.sequence} depends on missing step {dep}.")
            if dep >= step.sequence:
                raise WorkflowDependencyError(f"Step {step.sequence} cannot depend on future step {dep}.")


def resolve_execution_order(steps: list[PlanStepSpec]) -> list[PlanStepSpec]:
    """Stable topological order by sequence with dependency constraints."""
    by_seq = {step.sequence: step for step in steps}
    visited: set[int] = set()
    ordered: list[PlanStepSpec] = []

    def visit(seq: int) -> None:
        if seq in visited:
            return
        step = by_seq[seq]
        for dep in sorted(step.depends_on):
            visit(dep)
        visited.add(seq)
        ordered.append(step)

    for step in sorted(steps, key=lambda row: row.sequence):
        visit(step.sequence)
    return ordered