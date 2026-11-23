"""Adapter so legacy `ScreenUnderstandingUnavailable` callers can reach the live service."""

from app.automation.vision.contracts import OcrRequest, OcrResult, VisionQuestion, VisionResult
from app.automation.vision.image_pipeline import prepare_screenshot
from app.automation.vision.service import get_screen_intelligence_service, map_legacy_ocr
from app.automation.vision.providers.protocol import VisionTaskKind


class ScreenUnderstandingEngine:
    name = "vision"
    detail = "OCR and vision analysis via replaceable providers."

    def availability(self):
        return get_screen_intelligence_service().availability()

    async def extract_text(self, request: OcrRequest) -> OcrResult:
        shot = prepare_screenshot(request.image.data_base64)
        blocks = await get_screen_intelligence_service().run_ocr(shot)
        return map_legacy_ocr(blocks)

    async def answer(self, request: VisionQuestion) -> VisionResult:
        shot = prepare_screenshot(request.image.data_base64)
        analysis = await get_screen_intelligence_service().analyze(
            screenshot=shot,
            task=VisionTaskKind.ASK,
            question=request.question,
        )
        return VisionResult(answer=analysis.answer)