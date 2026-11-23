import asyncio
from uuid import uuid4

import pytest

from app.auth.permissions import ROLE_PERMISSIONS, Permission
from app.core.errors import UnknownToolError
from app.db.enums import UserRole
from app.tools.base import BaseTool
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk
from app.tools.errors import ToolTimeoutError
from app.tools.executor_service import ToolExecutorService
from app.tools.registry import ToolRegistry, build_registry
from app.tools.safe.schemas import CurrentTimeInput, CurrentTimeOutput
from pydantic import BaseModel


def _context(*, role: UserRole = UserRole.USER, confirmed: bool = True) -> ToolContext:
    return ToolContext(
        task_id=uuid4(),
        user_id=uuid4(),
        permissions=ROLE_PERMISSIONS[role],
        confirmed=confirmed,
    )


def test_registry_lists_safe_tools_with_metadata():
    registry = build_registry()
    names = registry.allowed_tool_names()
    assert "tool.current_time" in names
    assert "tool.calculate" in names
    assert "tool.app_status" in names
    assert "tool.text_transform" in names
    assert "mock.observe" in names
    metadata = registry.list_metadata()
    assert all(item.version.count(".") == 2 for item in metadata)


def test_valid_tool_calls():
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context()

    result = asyncio.run(executor.execute("tool.current_time", {}, context, registry))
    assert result.success is True
    assert result.data is not None
    assert "iso_utc" in result.data

    calc = asyncio.run(
        executor.execute("tool.calculate", {"expression": "(2 + 3) * 4"}, context, registry)
    )
    assert calc.success is True
    assert calc.data == {"value": 20.0}

    status = asyncio.run(executor.execute("tool.app_status", {}, context, registry))
    assert status.success is True
    assert status.data is not None
    assert status.data["service"] == "ScreenPilot"


def test_invalid_tool_inputs_return_structured_errors():
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context()

    missing = asyncio.run(executor.execute("tool.calculate", {}, context, registry))
    assert missing.success is False
    assert missing.error_code == "tool_validation_error"

    bad = asyncio.run(executor.execute("tool.calculate", {"expression": "__import__('os')"}, context, registry))
    assert bad.success is False
    assert bad.error_code == "tool_validation_error"


def test_unauthorized_tool_call():
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context(role=UserRole.USER)

    result = asyncio.run(executor.execute("tool.app_status.admin", {}, context, registry))
    assert result.success is False
    assert result.error_code == "tool_permission_denied"


def test_unknown_tool_raises():
    registry = build_registry()
    executor = ToolExecutorService()
    context = _context()

    with pytest.raises(UnknownToolError):
        asyncio.run(executor.execute("tool.missing", {}, context, registry))


class SlowOutput(BaseModel):
    ok: bool = True


class SlowTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="test.slow",
            version="1.0.0",
            description="Test-only slow tool.",
            risk=ToolRisk.LOW,
            required_permissions=[Permission.TASK_WRITE],
            timeout_seconds=0.05,
            input_schema="CurrentTimeInput",
            output_schema="SlowOutput",
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return CurrentTimeInput

    @property
    def output_model(self) -> type[BaseModel]:
        return SlowOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del payload, context
        await asyncio.sleep(0.2)
        return SlowOutput()


def test_tool_timeout():
    registry = ToolRegistry()
    registry.register(SlowTool())
    executor = ToolExecutorService()
    context = _context()

    result = asyncio.run(executor.execute("test.slow", {}, context, registry))
    assert result.success is False
    assert result.error_code == ToolTimeoutError.code


def test_tool_catalog_api_requires_auth(sqlite_app_client):
    client = sqlite_app_client
    unauth = client.get("/api/tools")
    assert unauth.status_code == 401

    register = client.post(
        "/api/auth/register",
        json={
            "email": "tools@example.com",
            "password": "valid-passphrase-1",
            "display_name": "tools",
        },
    )
    token = register.json()["access_token"]
    listing = client.get("/api/tools", headers={"Authorization": f"Bearer {token}"})
    assert listing.status_code == 200
    names = {row["name"] for row in listing.json()["tools"]}
    assert "tool.current_time" in names
    assert "tool.app_status.admin" in names