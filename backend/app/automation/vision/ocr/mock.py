import logging

from app.automation.vision.schemas import BoundingBox, OcrTextBlock, ProcessedScreenshot

logger = logging.getLogger("app.vision.ocr.mock")

_FIXTURE_BLOCKS: dict[str, list[OcrTextBlock]] = {}


def register_mock_ocr_fixture(sha256: str, blocks: list[OcrTextBlock]) -> None:
    _FIXTURE_BLOCKS[sha256] = blocks


def clear_mock_ocr_fixtures() -> None:
    _FIXTURE_BLOCKS.clear()


class MockOcrProvider:
    """Returns OCR only for registered fixture hashes — does not invent text."""

    name = "mock"

    async def extract(self, screenshot: ProcessedScreenshot) -> list[OcrTextBlock]:
        digest = screenshot.metadata.sha256
        blocks = _FIXTURE_BLOCKS.get(digest)
        if blocks is None:
            logger.info("mock_ocr_no_fixture", extra={"sha256": digest})
            return []
        return [block.model_copy() for block in blocks]


def default_hello_fixture_blocks() -> list[OcrTextBlock]:
    return [
        OcrTextBlock(
            text="Hello ScreenPilot",
            confidence=0.92,
            bbox=BoundingBox(x=20, y=70, width=220, height=24),
        ),
        OcrTextBlock(
            text="Submit button",
            confidence=0.88,
            bbox=BoundingBox(x=20, y=110, width=160, height=24),
        ),
    ]