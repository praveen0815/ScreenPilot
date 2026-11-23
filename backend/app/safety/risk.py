from enum import StrEnum

from app.tools.contracts import ToolMetadata, ToolRisk


class ActionRiskLevel(StrEnum):
    READ_ONLY = "read_only"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    RESTRICTED = "restricted"


_READ_ONLY_PREFIXES = ("tool.vision.",)
_LOW_PREFIXES = (
    "tool.current_time",
    "tool.app_status",
    "tool.calculate",
    "tool.text_transform",
    "tool.browser.session.",
    "tool.browser.navigate",
    "tool.browser.title",
    "tool.browser.text",
    "tool.browser.screenshot",
    "tool.browser.element.inspect",
    "tool.browser.wait",
    "tool.browser.form.fill",
    "tool.desktop.screenshot",
    "tool.desktop.mouse.position",
    "tool.desktop.display.info",
    "tool.desktop.window.active",
    "tool.desktop.wait",
    "mock.",
)
_MODERATE_TOOLS = frozenset(
    {
        "tool.browser.scroll",
        "tool.desktop.scroll",
        "tool.desktop.mouse.move",
    }
)
_HIGH_TOOLS = frozenset(
    {
        "tool.browser.click",
        "tool.browser.type",
        "tool.browser.form.submit",
        "tool.desktop.mouse.click",
        "tool.desktop.mouse.double_click",
        "tool.desktop.keyboard.type",
        "tool.desktop.keyboard.hotkey",
    }
)
_RESTRICTED_PREFIXES = (
    "tool.filesystem.",
    "tool.shell.",
    "tool.purchase.",
    "tool.payment.",
    "tool.email.send",
    "tool.credential.",
)


def classify_tool(metadata: ToolMetadata) -> ActionRiskLevel:
    name = metadata.name
    for prefix in _RESTRICTED_PREFIXES:
        if name.startswith(prefix):
            return ActionRiskLevel.RESTRICTED
    if any(name.startswith(prefix) for prefix in _READ_ONLY_PREFIXES):
        return ActionRiskLevel.READ_ONLY
    if name in _MODERATE_TOOLS:
        return ActionRiskLevel.MODERATE
    if name in _HIGH_TOOLS or metadata.risk is ToolRisk.HIGH:
        return ActionRiskLevel.HIGH
    if any(name.startswith(prefix) for prefix in _LOW_PREFIXES):
        return ActionRiskLevel.LOW
    if metadata.risk is ToolRisk.HIGH:
        return ActionRiskLevel.HIGH
    return ActionRiskLevel.LOW


SENSITIVE_PLAN_CATEGORIES = frozenset(
    {
        "purchase",
        "payment",
        "send_message",
        "delete_file",
        "submit_sensitive_form",
        "credential_access",
        "irreversible",
    }
)