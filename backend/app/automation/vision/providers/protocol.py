from enum import StrEnum
from typing import Protocol

from app.automation.vision.schemas import OcrTextBlock, ProcessedScreenshot, VisionAnalysisResponse


class VisionTaskKind(StrEnum):
    DESCRIBE = "describe"
    SUMMARIZE = "summarize"
    ASK = "ask"
    EXTRACT = "extract"
    ELEMENTS = "elements"
    NEXT_STEP = "next_step"


class VisionModelProvider(Protocol):
    name: str

    async def analyze(
        self,
        *,
        screenshot: ProcessedScreenshot,
        ocr_blocks: list[OcrTextBlock],
        task: VisionTaskKind,
        question: str | None = None,
    ) -> VisionAnalysisResponse: ...