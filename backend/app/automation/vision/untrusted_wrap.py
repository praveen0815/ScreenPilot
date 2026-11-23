from app.automation.vision.schemas import (
    OcrTextBlock,
    ProcessedScreenshot,
    VisionAnalysisResponse,
    VisibleElement,
)
from app.safety.untrusted import ObservationSource, UntrustedObservation


def join_ocr_text(blocks: list[OcrTextBlock]) -> str:
    return "\n".join(block.text for block in blocks if block.text.strip())


def wrap_untrusted(body: str, *, source: ObservationSource = ObservationSource.SCREEN) -> str:
    return UntrustedObservation(source=source, content=body).as_model_input()


def build_vision_response(
    *,
    screenshot: ProcessedScreenshot,
    answer: str,
    summary: str | None,
    ocr_blocks: list[OcrTextBlock],
    visible_elements: list[VisibleElement],
    confidence: float,
    uncertainty_notes: list[str],
) -> VisionAnalysisResponse:
    ocr_joined = join_ocr_text(ocr_blocks)
    untrusted_body = f"OCR text:\n{ocr_joined or '(none)'}\n\nAnalysis:\n{answer}"
    return VisionAnalysisResponse(
        answer=answer,
        summary=summary,
        ocr_blocks=ocr_blocks,
        visible_elements=visible_elements,
        confidence=max(0.0, min(confidence, 1.0)),
        uncertainty_notes=uncertainty_notes,
        metadata=screenshot.metadata,
        untrusted_context=wrap_untrusted(untrusted_body, source=ObservationSource.OCR),
    )