import re
from pydantic import BaseModel

from app.auth.permissions import Permission
from app.tools.base import BaseTool
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk
from app.tools.safe.schemas import TextTransformInput, TextTransformOp, TextTransformOutput


class TextTransformTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="tool.text_transform",
            version="1.0.0",
            description="Safely transform text using a fixed set of operations.",
            risk=ToolRisk.LOW,
            required_permissions=[Permission.TASK_WRITE],
            timeout_seconds=2.0,
            input_schema="TextTransformInput",
            output_schema="TextTransformOutput",
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return TextTransformInput

    @property
    def output_model(self) -> type[BaseModel]:
        return TextTransformOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del context
        assert isinstance(payload, TextTransformInput)
        text = payload.text
        if payload.operation is TextTransformOp.UPPER:
            result = text.upper()
        elif payload.operation is TextTransformOp.LOWER:
            result = text.lower()
        elif payload.operation is TextTransformOp.TRIM:
            result = text.strip()
        else:
            slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
            result = slug
        return TextTransformOutput(result=result)