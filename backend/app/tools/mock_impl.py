from pydantic import BaseModel, Field

from app.auth.permissions import Permission
from app.tools.base import BaseTool
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk


class MockObserveInput(BaseModel):
    target: str = Field(min_length=1, max_length=500)


class MockObserveOutput(BaseModel):
    observation: str


class MockObserveTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock.observe",
            version="1.0.0",
            description="Mock observation tool. Does not read the desktop or browser.",
            risk=ToolRisk.LOW,
            required_permissions=[Permission.TASK_WRITE],
            timeout_seconds=2.0,
            input_schema="MockObserveInput",
            output_schema="MockObserveOutput",
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return MockObserveInput

    @property
    def output_model(self) -> type[BaseModel]:
        return MockObserveOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del context
        assert isinstance(payload, MockObserveInput)
        return MockObserveOutput(observation=f"Observed context for: {payload.target[:200]}")


class MockSummarizeInput(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class MockSummarizeOutput(BaseModel):
    summary: str


class MockSummarizeTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock.summarize",
            version="1.0.0",
            description="Mock summarization tool. Does not call a language model.",
            risk=ToolRisk.LOW,
            required_permissions=[Permission.TASK_WRITE],
            timeout_seconds=2.0,
            input_schema="MockSummarizeInput",
            output_schema="MockSummarizeOutput",
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return MockSummarizeInput

    @property
    def output_model(self) -> type[BaseModel]:
        return MockSummarizeOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del context
        assert isinstance(payload, MockSummarizeInput)
        return MockSummarizeOutput(summary=payload.text[:500])