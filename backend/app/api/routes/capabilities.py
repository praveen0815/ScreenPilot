from fastapi import APIRouter

from app.agent.boundary import LangGraphRuntimeBoundary
from app.automation.browser import BrowserAutomationCapability
from app.automation.desktop import DesktopAutomationCapability
from app.automation.vision import ScreenUnderstandingCapability
from app.schemas.system import CapabilitiesResponse, CapabilityStatus
from app.tools.executor_service import ToolExecutorService

router = APIRouter(tags=["system"])


@router.get("/api/capabilities", response_model=CapabilitiesResponse)
async def capabilities() -> CapabilitiesResponse:
    engines = [
        LangGraphRuntimeBoundary(),
        BrowserAutomationCapability(),
        DesktopAutomationCapability(),
        ScreenUnderstandingCapability(),
        ToolExecutorService(),
    ]
    return CapabilitiesResponse(
        capabilities=[
            CapabilityStatus(name=engine.name, state=engine.availability(), detail=engine.detail)
            for engine in engines
        ]
    )
