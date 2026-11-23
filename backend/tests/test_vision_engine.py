import asyncio
import base64
import io
import os
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw

from app.auth.permissions import ROLE_PERMISSIONS
from app.automation.vision.ocr.mock import (
    clear_mock_ocr_fixtures,
    default_hello_fixture_blocks,
    register_mock_ocr_fixture,
)
from app.automation.vision.image_pipeline import prepare_screenshot
from app.core.config import get_settings
from app.db.enums import UserRole
from app.tools.contracts import ToolContext
from app.tools.executor_service import ToolExecutorService
from app.tools.registry import build_registry


def _hello_png_bytes() -> bytes:
    image = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 80), "Hello ScreenPilot", fill="black")
    draw.text((20, 120), "Submit button", fill="blue")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


@pytest.fixture
def vision_env():
    os.environ["VISION_ENABLED"] = "true"
    os.environ["VISION_OCR_PROVIDER"] = "mock"
    get_settings.cache_clear()
    clear_mock_ocr_fixtures()
    raw = _hello_png_bytes()
    shot = prepare_screenshot(_b64(raw))
    register_mock_ocr_fixture(shot.metadata.sha256, default_hello_fixture_blocks())
    yield raw
    clear_mock_ocr_fixtures()
    os.environ["VISION_ENABLED"] = "false"
    get_settings.cache_clear()


def _context() -> ToolContext:
    return ToolContext(
        task_id=uuid4(),
        user_id=uuid4(),
        permissions=ROLE_PERMISSIONS[UserRole.USER],
        confirmed=True,
    )


def test_image_validation_rejects_invalid_png(vision_env):
    del vision_env
    os.environ["VISION_ENABLED"] = "true"
    get_settings.cache_clear()
    with pytest.raises(Exception):
        prepare_screenshot(base64.b64encode(b"not-a-png").decode())


def test_image_pipeline_resizes_large_image(vision_env):
    del vision_env
    os.environ["VISION_ENABLED"] = "true"
    get_settings.cache_clear()
    large = Image.new("RGB", (3000, 2000), color="lightgray")
    buffer = io.BytesIO()
    large.save(buffer, format="PNG")
    shot = prepare_screenshot(_b64(buffer.getvalue()))
    assert shot.metadata.optimized is True
    assert shot.metadata.width <= get_settings().vision_max_width


@pytest.mark.asyncio
async def test_vision_ocr_and_describe_with_fixture(vision_env):
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context()
    payload = {"data_base64": _b64(vision_env)}

    ocr = await executor.execute("tool.vision.ocr", payload, context, registry)
    assert ocr.success is True
    assert any("Hello ScreenPilot" in block["text"] for block in ocr.data["blocks"])

    describe = await executor.execute("tool.vision.screen.describe", payload, context, registry)
    assert describe.success is True
    assert "Hello ScreenPilot" in describe.data["answer"]
    assert describe.data["untrusted_context"].startswith("UNTRUSTED OBSERVED CONTENT")
    assert describe.data["confidence"] > 0


@pytest.mark.asyncio
async def test_vision_does_not_fabricate_without_ocr(vision_env):
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context()
    blank = Image.new("RGB", (200, 120), color="white")
    buf = io.BytesIO()
    blank.save(buf, format="PNG")
    payload = {"data_base64": _b64(buf.getvalue())}

    describe = await executor.execute("tool.vision.screen.describe", payload, context, registry)
    assert describe.success is True
    assert "no readable text" in describe.data["answer"].lower()
    assert describe.data["ocr_blocks"] == []


@pytest.mark.asyncio
async def test_vision_ask_questions(vision_env):
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context()
    result = await executor.execute(
        "tool.vision.screen.ask",
        {"data_base64": _b64(vision_env), "question": "What buttons are visible on my screen?"},
        context,
        registry,
    )
    assert result.success is True
    assert "Submit" in result.data["answer"] or any("button" in e["kind"] for e in result.data["visible_elements"])


def test_instruction_injection_stays_untrusted(vision_env):
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context()
    result = asyncio.run(
        executor.execute(
            "tool.vision.screen.summarize",
            {"data_base64": _b64(vision_env)},
            context,
            registry,
        )
    )
    assert "UNTRUSTED OBSERVED CONTENT" in result.data["untrusted_context"]
    assert "security" in result.data["security_notice"].lower()