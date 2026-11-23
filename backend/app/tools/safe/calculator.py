from pydantic import BaseModel

from app.auth.permissions import Permission
from app.tools.base import BaseTool
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk
from app.tools.errors import ToolValidationError
from app.tools.safe.math_safe import safe_eval_expression
from app.tools.safe.schemas import CalculatorInput, CalculatorOutput


class CalculatorTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="tool.calculate",
            version="1.0.0",
            description="Evaluate a safe arithmetic expression (+, -, *, /, parentheses).",
            risk=ToolRisk.LOW,
            required_permissions=[Permission.TASK_WRITE],
            timeout_seconds=2.0,
            input_schema="CalculatorInput",
            output_schema="CalculatorOutput",
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return CalculatorInput

    @property
    def output_model(self) -> type[BaseModel]:
        return CalculatorOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del context
        assert isinstance(payload, CalculatorInput)
        try:
            value = safe_eval_expression(payload.expression)
        except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as exc:
            raise ToolValidationError("Calculator expression is invalid or unsafe.") from exc
        return CalculatorOutput(value=value)