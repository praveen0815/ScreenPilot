import asyncio
import io
import logging
from functools import partial

from PIL import Image

from app.automation.vision.errors import VisionOcrError
from app.automation.vision.schemas import BoundingBox, OcrTextBlock, ProcessedScreenshot

logger = logging.getLogger("app.vision.ocr.tesseract")


def _extract_sync(png_bytes: bytes) -> list[OcrTextBlock]:
    try:
        import pytesseract
    except ImportError as exc:
        raise VisionOcrError("pytesseract is not installed.") from exc

    image = Image.open(io.BytesIO(png_bytes))
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    blocks: list[OcrTextBlock] = []
    n = len(data.get("text", []))
    for index in range(n):
        text = (data["text"][index] or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][index])
        except (TypeError, ValueError):
            conf = 0.0
        confidence = max(0.0, min(conf / 100.0, 1.0))
        left = int(data["left"][index])
        top = int(data["top"][index])
        width = int(data["width"][index])
        height = int(data["height"][index])
        bbox = BoundingBox(x=left, y=top, width=width, height=height) if width and height else None
        blocks.append(OcrTextBlock(text=text[:2000], confidence=confidence, bbox=bbox))
    return blocks


class TesseractOcrProvider:
    name = "tesseract"

    async def extract(self, screenshot: ProcessedScreenshot) -> list[OcrTextBlock]:
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None, partial(_extract_sync, screenshot.png_bytes)
            )
        except VisionOcrError:
            raise
        except Exception as exc:
            logger.exception("tesseract_ocr_failed")
            raise VisionOcrError("Tesseract OCR failed.") from exc