from pydantic import BaseModel, Field

from app.auth.permissions import Permission
from app.tools.base import BaseTool
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk
from app.tools.errors import ToolError


class MockWorkflowAttemptInput(BaseModel):
    probe: str = Field(min_length=1, max_length=120)
    fail_until_attempt: int = Field(default=2, ge=1, le=10)
    attempt: int = Field(default=1, ge=1, le=20)


class MockWorkflowAttemptOutput(BaseModel):
    probe: str
    attempt: int
    status: str


class MockWorkflowAttemptTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mock.workflow.attempt",
            version="1.0.0",
            description="Controlled workflow probe that fails until a given attempt number.",
            risk=ToolRisk.LOW,
            required_permissions=[Permission.TASK_WRITE],
            timeout_seconds=2.0,
            input_schema="MockWorkflowAttemptInput",
            output_schema="MockWorkflowAttemptOutput",
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return MockWorkflowAttemptInput

    @property
    def output_model(self) -> type[BaseModel]:
        return MockWorkflowAttemptOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del context
        assert isinstance(payload, MockWorkflowAttemptInput)
        if payload.attempt < payload.fail_until_attempt:
            raise ToolError(f"Probe {payload.probe} failed on attempt {payload.attempt}.")
        return MockWorkflowAttemptOutput(
            probe=payload.probe,
            attempt=payload.attempt,
            status="ok",
        )