import base64
import hashlib
import io
import logging

from PIL import Image

from app.automation.vision.errors import VisionImageValidationError
from app.automation.vision.schemas import ProcessedScreenshot, ScreenshotMetadata
from app.core.config import Settings, get_settings

logger = logging.getLogger("app.vision.pipeline")


def _png_magic(data: bytes) -> bool:
    return data.startswith(b"\x89PNG\r\n\x1a\n")


def prepare_screenshot(data_base64: str, *, settings: Settings | None = None) -> ProcessedScreenshot:
    active = settings or get_settings()
    if not active.vision_enabled:
        from app.automation.vision.errors import VisionDisabledError

        raise VisionDisabledError("Vision is disabled.")

    try:
        raw = base64.b64decode(data_base64, validate=True)
    except Exception as exc:
        raise VisionImageValidationError("Invalid base64 image payload.") from exc

    if len(raw) > active.vision_max_image_bytes:
        raise VisionImageValidationError("Image exceeds maximum allowed size.")
    if not _png_magic(raw):
        raise VisionImageValidationError("Only PNG screenshots are supported.")

    digest = hashlib.sha256(raw).hexdigest()
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception as exc:
        raise VisionImageValidationError("Could not decode PNG image.") from exc

    source_width, source_height = image.size
    if source_width <= 0 or source_height <= 0:
        raise VisionImageValidationError("Image dimensions are invalid.")

    optimized = False
    max_w = active.vision_max_width
    max_h = active.vision_max_height
    working = image.convert("RGBA") if image.mode not in {"RGB", "RGBA"} else image
    if source_width > max_w or source_height > max_h:
        working.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        optimized = True

    buffer = io.BytesIO()
    working.save(buffer, format="PNG", optimize=True, compress_level=active.vision_png_compress_level)
    png_bytes = buffer.getvalue()
    width, height = working.size

    metadata = ScreenshotMetadata(
        content_type="image/png",
        sha256=digest,
        width=width,
        height=height,
        byte_length=len(png_bytes),
        optimized=optimized,
        source_width=source_width,
        source_height=source_height,
    )
    logger.info(
        "vision_image_prepared",
        extra={
            "sha256": digest,
            "width": width,
            "height": height,
            "optimized": optimized,
        },
    )
    return ProcessedScreenshot(png_bytes=png_bytes, metadata=metadata)