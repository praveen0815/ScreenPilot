from pydantic import BaseModel, ConfigDict, Field

from app.automation.vision.schemas import (
    OcrTextBlock,
    ScreenshotMetadata,
    VisionAnalysisResponse,
    VisibleElement,
)


class VisionImageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_base64: str = Field(min_length=1, max_length=8_000_000)


class VisionAskInput(VisionImageInput):
    question: str = Field(min_length=1, max_length=1000)


class PrepareOutput(BaseModel):
    metadata: ScreenshotMetadata


class OcrOutput(BaseModel):
    metadata: ScreenshotMetadata
    blocks: list[OcrTextBlock]
    untrusted_context: str
    security_notice: str


class VisionToolOutput(BaseModel):
    answer: str
    summary: str | None = None
    confidence: float
    uncertainty_notes: list[str]
    metadata: ScreenshotMetadata
    ocr_blocks: list[OcrTextBlock] = Field(default_factory=list)
    visible_elements: list[VisibleElement] = Field(default_factory=list)
    untrusted_context: str
    security_notice: str


def analysis_to_tool_output(response: VisionAnalysisResponse) -> VisionToolOutput:
    return VisionToolOutput(
        answer=response.answer,
        summary=response.summary,
        confidence=response.confidence,
        uncertainty_notes=response.uncertainty_notes,
        metadata=response.metadata,
        ocr_blocks=response.ocr_blocks,
        visible_elements=response.visible_elements,
        untrusted_context=response.untrusted_context,
        security_notice=response.security_notice,
    )