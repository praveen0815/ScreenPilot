"""Confirmation rules for future actions.

The policy is active. No Phase 1 code path executes an action that would consult it.
"""

from app.safety.risk import ActionRiskLevel, SENSITIVE_PLAN_CATEGORIES
from app.tools.contracts import ToolRisk

HIGH_RISK_CATEGORIES = frozenset(SENSITIVE_PLAN_CATEGORIES) | frozenset(
    {
        "purchase",
        "send_message",
        "delete_file",
        "submit_sensitive_form",
        "irreversible",
    }
)


def requires_confirmation(risk: ToolRisk, category: str | None = None) -> bool:
    if risk is ToolRisk.HIGH:
        return True
    return category in HIGH_RISK_CATEGORIES


def requires_approval_for_action(level: ActionRiskLevel, category: str | None = None) -> bool:
    if level in {ActionRiskLevel.HIGH, ActionRiskLevel.RESTRICTED}:
        return True
    if level is ActionRiskLevel.MODERATE:
        return True
    return requires_confirmation(ToolRisk.LOW, category)
