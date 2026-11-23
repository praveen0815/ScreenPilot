from app.automation.desktop.capability import DesktopAutomationCapability
from app.automation.desktop.contracts import (
    DesktopAction,
    DesktopAutomationUnavailable,
    DesktopCommand,
    DesktopObservation,
)
from app.automation.desktop.safety import get_desktop_safety_gate
from app.automation.desktop.service import DesktopAutomationService, get_desktop_automation_service

__all__ = [
    "DesktopAction",
    "DesktopAutomationCapability",
    "DesktopAutomationService",
    "DesktopAutomationUnavailable",
    "DesktopCommand",
    "DesktopObservation",
    "get_desktop_automation_service",
    "get_desktop_safety_gate",
]