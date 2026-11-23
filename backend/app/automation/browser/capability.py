from typing import Literal

from app.core.config import get_settings


class BrowserAutomationCapability:
    name = "browser"
    detail = "Chromium browser automation via Playwright with validated URLs and scoped sessions."

    def availability(self) -> Literal["unavailable", "available"]:
        settings = get_settings()
        if not settings.browser_enabled:
            return "unavailable"
        return "available"