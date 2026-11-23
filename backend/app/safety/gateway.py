import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import Permission
from app.core.config import get_settings
from app.memory.sanitize import MemoryPolicyError, sanitize_text_for_memory
from app.safety.audit import log_blocked_action
from app.safety.injection import is_policy_override_attempt
from app.safety.risk import ActionRiskLevel, SENSITIVE_PLAN_CATEGORIES, classify_tool
from app.safety.tool_permissions import required_tool_permissions
from app.tools.contracts import ToolMetadata, ToolContext
from app.tools.errors import ToolPermissionError


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reason: str | None = None
    risk: ActionRiskLevel | None = None
    requires_confirmation: bool = False


def _arguments_contain_secrets(arguments: Mapping[str, Any]) -> bool:
    blob = json.dumps(dict(arguments), default=str).lower()
    if any(token in blob for token in ("password", "api_key", "apikey", "bearer", "secret", "credential")):
        return True
    for key in arguments:
        if str(key).lower() in {"shell", "command", "code", "script"}:
            return True
    return False


def evaluate_tool_safety(
    *,
    metadata: ToolMetadata,
    context: ToolContext,
    arguments: Mapping[str, Any],
    user_grants: frozenset[Permission] | None = None,
) -> SafetyDecision:
    settings = get_settings()
    risk = classify_tool(metadata)
    grants = user_grants if user_grants is not None else context.permissions

    if context.user_id is None:
        return SafetyDecision(allowed=False, reason="Authenticated user context is required.", risk=risk)

    if risk is ActionRiskLevel.RESTRICTED:
        return SafetyDecision(
            allowed=False,
            reason=f"Tool '{metadata.name}' is restricted and cannot be executed.",
            risk=risk,
        )

    if metadata.name.startswith(("tool.purchase.", "tool.payment.")):
        return SafetyDecision(allowed=False, reason="Purchase and payment tools are prohibited.", risk=risk)

    if "purchase" in metadata.name or "payment" in metadata.name:
        return SafetyDecision(allowed=False, reason="Purchase and payment actions are prohibited.", risk=risk)

    if _arguments_contain_secrets(arguments):
        return SafetyDecision(allowed=False, reason="Credential or secret fields are prohibited.", risk=risk)

    for value in arguments.values():
        if isinstance(value, str) and is_policy_override_attempt(value):
            return SafetyDecision(
                allowed=False,
                reason="Untrusted content attempted to override safety policy.",
                risk=risk,
            )

    missing = [perm for perm in required_tool_permissions(metadata) if perm not in grants]
    if missing:
        return SafetyDecision(
            allowed=False,
            reason=f"Missing permissions: {', '.join(item.value for item in missing)}.",
            risk=risk,
        )

    if Permission.TOOL_FILESYSTEM in required_tool_permissions(metadata):
        return SafetyDecision(allowed=False, reason="Filesystem tools are not enabled.", risk=risk)

    if metadata.name.startswith("tool.purchase") or Permission.PURCHASE_EXECUTE in required_tool_permissions(metadata):
        if Permission.PURCHASE_EXECUTE not in grants:
            return SafetyDecision(
                allowed=False,
                reason="Purchase execution is not authorized for this user.",
                risk=risk,
            )

    requires_confirmation = risk in {ActionRiskLevel.HIGH, ActionRiskLevel.MODERATE}
    if settings.safety_require_approval_for_moderate and risk is ActionRiskLevel.MODERATE:
        requires_confirmation = True
    if risk is ActionRiskLevel.HIGH and not context.confirmed:
        return SafetyDecision(
            allowed=False,
            reason=f"Tool '{metadata.name}' requires explicit approval.",
            risk=risk,
            requires_confirmation=True,
        )
    if (
        settings.safety_require_approval_for_moderate
        and risk is ActionRiskLevel.MODERATE
        and not context.confirmed
    ):
        return SafetyDecision(
            allowed=False,
            reason=f"Tool '{metadata.name}' requires approval for moderate-risk actions.",
            risk=risk,
            requires_confirmation=True,
        )

    return SafetyDecision(allowed=True, risk=risk, requires_confirmation=requires_confirmation)


async def enforce_tool_safety(
    session: AsyncSession | None,
    *,
    metadata: ToolMetadata,
    context: ToolContext,
    arguments: Mapping[str, Any],
) -> None:
    decision = evaluate_tool_safety(metadata=metadata, context=context, arguments=arguments)
    if decision.allowed:
        return
    if session is not None:
        await log_blocked_action(
            session,
            user_id=context.user_id,
            task_id=context.task_id,
            tool_name=metadata.name,
            reason=decision.reason or "blocked",
        )
    raise ToolPermissionError(decision.reason or "Action blocked by safety policy.")


def plan_contains_prohibited_category(categories: list[str]) -> str | None:
    for category in categories:
        if category in SENSITIVE_PLAN_CATEGORIES:
            if category in {"purchase", "payment"}:
                return "Purchase and payment require explicit authorization and are blocked in this build."
            return f"Plan category '{category}' requires approval and may be blocked."
    return None