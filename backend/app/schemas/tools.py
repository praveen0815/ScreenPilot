from pydantic import BaseModel, ConfigDict, Field

from app.tools.contracts import ToolMetadata


class ToolMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    description: str
    risk: str
    required_permissions: list[str]
    timeout_seconds: float
    input_schema: str
    output_schema: str
    available: bool


class ToolCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tools: list[ToolMetadataResponse] = Field(default_factory=list)


def tool_metadata_to_response(item: ToolMetadata) -> ToolMetadataResponse:
    return ToolMetadataResponse(
        name=item.name,
        version=item.version,
        description=item.description,
        risk=item.risk.value,
        required_permissions=[perm.value for perm in item.required_permissions],
        timeout_seconds=item.timeout_seconds,
        input_schema=item.input_schema,
        output_schema=item.output_schema,
        available=item.available,
    )