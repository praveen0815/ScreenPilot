from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.db.models.user import User
from app.schemas.tools import ToolCatalogResponse, tool_metadata_to_response
from app.tools.registry import build_registry

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("", response_model=ToolCatalogResponse)
async def list_tools(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ToolCatalogResponse:
    del current_user
    registry = build_registry()
    return ToolCatalogResponse(
        tools=[tool_metadata_to_response(item) for item in registry.list_metadata() if item.available]
    )