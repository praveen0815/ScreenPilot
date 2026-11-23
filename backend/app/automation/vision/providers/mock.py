import re

from app.automation.vision.schemas import (
    OcrTextBlock,
    ProcessedScreenshot,
    VisionAnalysisResponse,
    VisibleElement,
)
from app.automation.vision.providers.protocol import VisionTaskKind
from app.automation.vision.untrusted_wrap import build_vision_response, join_ocr_text


class MockVisionModelProvider:
    """Derives answers only from OCR blocks — never fabricates unseen screen content."""

    name = "mock"

    def _elements(self, blocks: list[OcrTextBlock]) -> list[VisibleElement]:
        elements: list[VisibleElement] = []
        for block in blocks:
            elements.append(
                VisibleElement(
                    kind="text",
                    label=block.text,
                    confidence=block.confidence,
                    bbox=block.bbox,
                )
            )
            if re.search(r"\b(button|submit|ok|cancel)\b", block.text, re.I):
                elements.append(
                    VisibleElement(
                        kind="button_like",
                        label=block.text,
                        confidence=max(0.4, block.confidence - 0.1),
                        bbox=block.bbox,
                    )
                )
        return elements

    async def analyze(
        self,
        *,
        screenshot: ProcessedScreenshot,
        ocr_blocks: list[OcrTextBlock],
        task: VisionTaskKind,
        question: str | None = None,
    ) -> VisionAnalysisResponse:
        joined = join_ocr_text(ocr_blocks)
        uncertainty: list[str] = []
        confidence = 0.0
        if ocr_blocks:
            confidence = sum(block.confidence for block in ocr_blocks) / len(ocr_blocks)
        else:
            uncertainty.append("No OCR text was extracted; vision output may be empty.")
            confidence = 0.2

        uncertainty.append("Mock vision provider does not run a multimodal model.")
        uncertainty.append("Visual element detection is OCR-heuristic only.")

        elements = self._elements(ocr_blocks)
        summary: str | None = None
        answer = ""

        if task is VisionTaskKind.DESCRIBE:
            answer = (
                "Based on OCR only: "
                + (joined if joined else "no readable text was detected in the screenshot.")
            )
        elif task is VisionTaskKind.SUMMARIZE:
            summary = joined[:500] if joined else "No text available to summarize."
            answer = summary
        elif task is VisionTaskKind.EXTRACT:
            answer = joined or "No extractable text."
        elif task is VisionTaskKind.ELEMENTS:
            if not elements:
                answer = "No visible text or button-like strings detected via OCR."
            else:
                labels = ", ".join(element.label for element in elements[:20])
                answer = f"OCR-derived visible items: {labels}"
        elif task is VisionTaskKind.NEXT_STEP:
            if not joined:
                answer = "Insufficient OCR data to suggest a next step."
                uncertainty.append("Low confidence suggestion withheld.")
            else:
                answer = (
                    "Consider reviewing the visible text on screen. "
                    "Any action still requires normal agent approvals and policy checks."
                )
                confidence = min(confidence, 0.55)
                uncertainty.append("Suggested next step is generic and not inferred from hidden UI state.")
        else:
            q = (question or "").strip().lower()
            if not joined:
                answer = "No OCR text available to answer that question."
            elif "what is displayed" in q or "on my screen" in q:
                answer = joined
            elif "summarize" in q:
                answer = joined[:400]
            elif "button" in q or "text" in q:
                labels = ", ".join(element.label for element in elements) or joined
                answer = f"From OCR: {labels}"
            elif "what should i do next" in q or "next" in q:
                answer = (
                    "Based only on OCR-visible text, verify the screen matches your intent "
                    "before approving any high-risk tool step."
                )
                confidence = min(confidence, 0.55)
            else:
                answer = f"OCR-visible context related to your question: {joined[:600]}"
                uncertainty.append("Question answered from OCR text only, not a full vision model.")

        return build_vision_response(
            screenshot=screenshot,
            answer=answer,
            summary=summary,
            ocr_blocks=ocr_blocks,
            visible_elements=elements if task in {VisionTaskKind.ELEMENTS, VisionTaskKind.ASK, VisionTaskKind.DESCRIBE} else elements[:10],
            confidence=confidence,
            uncertainty_notes=uncertainty,
        )