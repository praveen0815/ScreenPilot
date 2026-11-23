from typing import Literal

from app.automation.desktop.service import DesktopAutomationService
from app.core.config import get_settings


class DesktopAutomationCapability:
    name = "desktop"
    detail = DesktopAutomationService().detail

    def availability(self) -> Literal["unavailable", "available"]:
        if not get_settings().desktop_enabled:
            return "unavailable"
        return "available"