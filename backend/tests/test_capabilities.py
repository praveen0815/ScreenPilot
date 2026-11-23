from app.agent.boundary import LangGraphRuntimeBoundary
from app.automation.browser import BrowserAutomationUnavailable
from app.automation.desktop import DesktopAutomationUnavailable
from app.automation.vision import ScreenUnderstandingUnavailable
from app.tools.mock_executor import MockToolExecutor


def test_capabilities_report_mock_agent_and_tools(client):
    response = client.get("/api/capabilities")

    assert response.status_code == 200
    capabilities = response.json()["capabilities"]
    assert [item["name"] for item in capabilities] == [
        "agent",
        "browser",
        "desktop",
        "vision",
        "tools",
    ]
    states = [item["state"] for item in capabilities]
    assert states[0] == "mock"
    assert states[4] == "available"
    assert states[1:4] == ["unavailable"] * 3
    assert capabilities[0]["detail"] == LangGraphRuntimeBoundary.detail
    assert capabilities[4]["detail"] == MockToolExecutor.detail