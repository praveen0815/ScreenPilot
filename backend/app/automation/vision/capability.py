from typing import Literal

from app.core.config import get_settings


class ScreenUnderstandingCapability:
    name = "vision"
    detail = "Screenshot validation, OCR, and replaceable mock vision analysis."

    def availability(self) -> Literal["unavailable", "available"]:
        if get_settings().vision_enabled:
            return "available"
        return "unavailable"