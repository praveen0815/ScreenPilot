from typing import Protocol

from app.automation.vision.schemas import OcrTextBlock, ProcessedScreenshot


class OcrProvider(Protocol):
    name: str

    async def extract(self, screenshot: ProcessedScreenshot) -> list[OcrTextBlock]: ...