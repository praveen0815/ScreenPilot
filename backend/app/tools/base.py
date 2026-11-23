from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ValidationError

from app.tools.contracts import ToolContext, ToolMetadata, ToolResult
from app.tools.errors import ToolValidationError


class BaseTool(ABC):
    """Registered tools must declare Pydantic input/output models and metadata."""

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata: ...

    @property
    @abstractmethod
    def input_model(self) -> type[BaseModel]: ...

    @property
    @abstractmethod
    def output_model(self) -> type[BaseModel]: ...

    def parse_input(self, arguments: Mapping[str, Any]) -> BaseModel:
        try:
            return self.input_model.model_validate(dict(arguments))
        except ValidationError as exc:
            raise ToolValidationError(f"Invalid arguments for {self.metadata.name}.") from exc

    @abstractmethod
    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel: ...

    async def validate(self, arguments: Mapping[str, Any]) -> None:
        self.parse_input(arguments)

    async def execute(self, arguments: Mapping[str, Any], context: ToolContext) -> ToolResult:
        payload = self.parse_input(arguments)
        output = await self.invoke(payload, context)
        if not isinstance(output, self.output_model):
            raise ToolValidationError("Tool returned an unexpected output type.")
        data = output.model_dump()
        return ToolResult(success=True, output=output.model_dump_json(), data=data)