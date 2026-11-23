import logging

from app.automation.vision.errors import VisionDisabledError, VisionError
from app.automation.vision.image_pipeline import prepare_screenshot
from app.automation.vision.ocr.mock import MockOcrProvider
from app.automation.vision.ocr.protocol import OcrProvider
from app.automation.vision.ocr.tesseract import TesseractOcrProvider
from app.automation.vision.providers.mock import MockVisionModelProvider
from app.automation.vision.providers.protocol import VisionModelProvider, VisionTaskKind
from app.automation.vision.schemas import OcrTextBlock, ProcessedScreenshot, VisionAnalysisResponse
from app.core.config import Settings, get_settings

logger = logging.getLogger("app.vision.service")

_service: "ScreenIntelligenceService | None" = None


def get_ocr_provider(settings: Settings) -> OcrProvider:
    if settings.vision_ocr_provider == "tesseract":
        return TesseractOcrProvider()
    return MockOcrProvider()


def get_vision_provider(settings: Settings) -> VisionModelProvider:
    if settings.vision_model_provider == "mock":
        return MockVisionModelProvider()
    return MockVisionModelProvider()


class ScreenIntelligenceService:
    name = "vision"
    detail = "Screenshot OCR and mock vision analysis with untrusted content wrapping."

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def availability(self) -> str:
        return "available" if self._settings.vision_enabled else "unavailable"

    def _require_enabled(self) -> None:
        if not self._settings.vision_enabled:
            raise VisionDisabledError("Vision is disabled.")

    async def prepare(self, data_base64: str) -> ProcessedScreenshot:
        self._require_enabled()
        return prepare_screenshot(data_base64, settings=self._settings)

    async def run_ocr(self, screenshot: ProcessedScreenshot) -> list[OcrTextBlock]:
        self._require_enabled()
        provider = get_ocr_provider(self._settings)
        blocks = await provider.extract(screenshot)
        logger.info(
            "vision_ocr_complete",
            extra={"provider": provider.name, "blocks": len(blocks), "sha256": screenshot.metadata.sha256},
        )
        return blocks

    async def analyze(
        self,
        *,
        screenshot: ProcessedScreenshot,
        task: VisionTaskKind,
        question: str | None = None,
        ocr_blocks: list[OcrTextBlock] | None = None,
    ) -> VisionAnalysisResponse:
        self._require_enabled()
        blocks = ocr_blocks if ocr_blocks is not None else await self.run_ocr(screenshot)
        provider = get_vision_provider(self._settings)
        return await provider.analyze(
            screenshot=screenshot,
            ocr_blocks=blocks,
            task=task,
            question=question,
        )


def get_screen_intelligence_service() -> ScreenIntelligenceService:
    global _service
    if _service is None:
        _service = ScreenIntelligenceService()
    return _service


def map_legacy_ocr(blocks: list[OcrTextBlock]):
    from app.automation.vision.contracts import OcrBlock, OcrResult

    return OcrResult(
        blocks=[OcrBlock(text=block.text, confidence=block.confidence) for block in blocks],
    )