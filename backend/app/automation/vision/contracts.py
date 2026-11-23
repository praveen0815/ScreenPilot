"""Legacy vision contract (Phase 1 compatibility)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.automation.vision.schemas import OcrTextBlock, ScreenImageInput
from app.core.errors import AutomationUnavailableError


# Backward-compatible alias
ScreenImage = ScreenImageInput


class OcrRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image: ScreenImageInput


class VisionQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image: ScreenImageInput
    question: str = Field(min_length=1, max_length=1000)


class OcrBlock(BaseModel):
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class OcrResult(BaseModel):
    blocks: list[OcrBlock]


class VisionResult(BaseModel):
    answer: str


class ScreenUnderstandingUnavailable:
    name = "vision"
    detail = "Vision and OCR are not enabled in this build."

    def availability(self) -> Literal["unavailable"]:
        return "unavailable"

    async def extract_text(self, request: OcrRequest) -> OcrResult:
        del request
        raise AutomationUnavailableError("vision")

    async def answer(self, request: VisionQuestion) -> VisionResult:
        del request
        raise AutomationUnavailableError("vision")