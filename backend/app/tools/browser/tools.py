from pydantic import BaseModel

from app.tools.base import BaseTool
from app.tools.browser.common import browser_meta, require_browser_user, run_browser, service
from app.tools.browser.schemas import (
    ClickInput,
    ClickOutput,
    FormFillInput,
    FormFillOutput,
    FormSubmitInput,
    FormSubmitOutput,
    InspectInput,
    InspectOutput,
    NavigateInput,
    NavigateOutput,
    ScreenshotInput,
    ScreenshotOutput,
    ScrollInput,
    ScrollOutput,
    SessionCloseInput,
    SessionCloseOutput,
    SessionCreateInput,
    SessionCreateOutput,
    TextInput,
    TextOutput,
    TitleInput,
    TitleOutput,
    TypeInput,
    TypeOutput,
    WaitInput,
    WaitOutput,
)
from app.tools.contracts import ToolContext, ToolMetadata, ToolRisk


class BrowserSessionCreateTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.session.create",
            description="Create an isolated Chromium browser session for this task.",
            risk=ToolRisk.LOW,
            input_schema="SessionCreateInput",
            output_schema="SessionCreateOutput",
            timeout_seconds=30.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return SessionCreateInput

    @property
    def output_model(self) -> type[BaseModel]:
        return SessionCreateOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        del payload
        user_id, task_id = require_browser_user(context)
        session_id = await run_browser(service().create_session(user_id=user_id, task_id=task_id))
        return SessionCreateOutput(session_id=session_id)


class BrowserSessionCloseTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.session.close",
            description="Close a browser session and release resources.",
            risk=ToolRisk.LOW,
            input_schema="SessionCloseInput",
            output_schema="SessionCloseOutput",
            timeout_seconds=20.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return SessionCloseInput

    @property
    def output_model(self) -> type[BaseModel]:
        return SessionCloseOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, SessionCloseInput)
        user_id, task_id = require_browser_user(context)
        count = await run_browser(
            service().close_session(
                session_id=payload.session_id,
                user_id=user_id,
                task_id=task_id,
            )
        )
        return SessionCloseOutput(actions_recorded=count)


class BrowserNavigateTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.navigate",
            description="Navigate the session to a validated http(s) URL.",
            risk=ToolRisk.LOW,
            input_schema="NavigateInput",
            output_schema="NavigateOutput",
            timeout_seconds=60.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return NavigateInput

    @property
    def output_model(self) -> type[BaseModel]:
        return NavigateOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, NavigateInput)
        user_id, task_id = require_browser_user(context)
        data = await run_browser(
            service().navigate(
                session_id=payload.session_id,
                user_id=user_id,
                task_id=task_id,
                url=payload.url,
            )
        )
        return NavigateOutput(**data)


class BrowserTitleTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.title",
            description="Read the current page title.",
            risk=ToolRisk.LOW,
            input_schema="TitleInput",
            output_schema="TitleOutput",
            timeout_seconds=10.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return TitleInput

    @property
    def output_model(self) -> type[BaseModel]:
        return TitleOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, TitleInput)
        user_id, task_id = require_browser_user(context)
        title = await run_browser(
            service().get_title(session_id=payload.session_id, user_id=user_id, task_id=task_id)
        )
        return TitleOutput(title=title)


class BrowserTextTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.text",
            description="Extract visible text from the current page.",
            risk=ToolRisk.LOW,
            input_schema="TextInput",
            output_schema="TextOutput",
            timeout_seconds=20.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return TextInput

    @property
    def output_model(self) -> type[BaseModel]:
        return TextOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, TextInput)
        user_id, task_id = require_browser_user(context)
        text = await run_browser(
            service().get_visible_text(session_id=payload.session_id, user_id=user_id, task_id=task_id)
        )
        return TextOutput(text=text)


class BrowserScreenshotTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.screenshot",
            description="Capture a PNG screenshot of the current viewport.",
            risk=ToolRisk.LOW,
            input_schema="ScreenshotInput",
            output_schema="ScreenshotOutput",
            timeout_seconds=20.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return ScreenshotInput

    @property
    def output_model(self) -> type[BaseModel]:
        return ScreenshotOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, ScreenshotInput)
        user_id, task_id = require_browser_user(context)
        data = await run_browser(
            service().screenshot(session_id=payload.session_id, user_id=user_id, task_id=task_id)
        )
        return ScreenshotOutput(**data)


class BrowserInspectTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.element.inspect",
            description="Inspect a single element by CSS selector.",
            risk=ToolRisk.LOW,
            input_schema="InspectInput",
            output_schema="InspectOutput",
            timeout_seconds=20.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return InspectInput

    @property
    def output_model(self) -> type[BaseModel]:
        return InspectOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, InspectInput)
        user_id, task_id = require_browser_user(context)
        data = await run_browser(
            service().inspect_element(
                session_id=payload.session_id,
                user_id=user_id,
                task_id=task_id,
                selector=payload.selector,
            )
        )
        return InspectOutput(**data)


class BrowserClickTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.click",
            description="Click an element. Requires approval when marked high-risk in the plan.",
            risk=ToolRisk.HIGH,
            input_schema="ClickInput",
            output_schema="ClickOutput",
            timeout_seconds=20.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return ClickInput

    @property
    def output_model(self) -> type[BaseModel]:
        return ClickOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, ClickInput)
        user_id, task_id = require_browser_user(context)
        data = await run_browser(
            service().click(
                session_id=payload.session_id,
                user_id=user_id,
                task_id=task_id,
                selector=payload.selector,
            )
        )
        return ClickOutput(**data)


class BrowserTypeTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.type",
            description="Type into an input field. Requires approval when marked high-risk in the plan.",
            risk=ToolRisk.HIGH,
            input_schema="TypeInput",
            output_schema="TypeOutput",
            timeout_seconds=20.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return TypeInput

    @property
    def output_model(self) -> type[BaseModel]:
        return TypeOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, TypeInput)
        user_id, task_id = require_browser_user(context)
        data = await run_browser(
            service().type_text(
                session_id=payload.session_id,
                user_id=user_id,
                task_id=task_id,
                selector=payload.selector,
                text=payload.text,
                clear_first=payload.clear_first,
            )
        )
        return TypeOutput(**data)


class BrowserScrollTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.scroll",
            description="Scroll the page or bring an element into view.",
            risk=ToolRisk.LOW,
            input_schema="ScrollInput",
            output_schema="ScrollOutput",
            timeout_seconds=15.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return ScrollInput

    @property
    def output_model(self) -> type[BaseModel]:
        return ScrollOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, ScrollInput)
        if payload.selector is None and payload.delta_y == 0:
            from app.tools.errors import ToolValidationError

            raise ToolValidationError("Provide selector or a non-zero delta_y.")
        user_id, task_id = require_browser_user(context)
        data = await run_browser(
            service().scroll(
                session_id=payload.session_id,
                user_id=user_id,
                task_id=task_id,
                delta_y=payload.delta_y,
                selector=payload.selector,
            )
        )
        return ScrollOutput(**data)


class BrowserWaitTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.wait",
            description="Wait for an element to reach a DOM state.",
            risk=ToolRisk.LOW,
            input_schema="WaitInput",
            output_schema="WaitOutput",
            timeout_seconds=65.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return WaitInput

    @property
    def output_model(self) -> type[BaseModel]:
        return WaitOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, WaitInput)
        user_id, task_id = require_browser_user(context)
        data = await run_browser(
            service().wait_for_element(
                session_id=payload.session_id,
                user_id=user_id,
                task_id=task_id,
                selector=payload.selector,
                state=payload.state.value,
                timeout_ms=payload.timeout_ms,
            )
        )
        return WaitOutput(**data)


class BrowserFormFillTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.form.fill",
            description="Fill form fields without submitting.",
            risk=ToolRisk.LOW,
            input_schema="FormFillInput",
            output_schema="FormFillOutput",
            timeout_seconds=30.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return FormFillInput

    @property
    def output_model(self) -> type[BaseModel]:
        return FormFillOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, FormFillInput)
        user_id, task_id = require_browser_user(context)
        fields = [(field.selector, field.value) for field in payload.fields]
        data = await run_browser(
            service().fill_form(
                session_id=payload.session_id,
                user_id=user_id,
                task_id=task_id,
                fields=fields,
            )
        )
        return FormFillOutput(**data)


class BrowserFormSubmitTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return browser_meta(
            name="tool.browser.form.submit",
            description="Submit a form via a button or submit control. Requires approval.",
            risk=ToolRisk.HIGH,
            input_schema="FormSubmitInput",
            output_schema="FormSubmitOutput",
            timeout_seconds=45.0,
        )

    @property
    def input_model(self) -> type[BaseModel]:
        return FormSubmitInput

    @property
    def output_model(self) -> type[BaseModel]:
        return FormSubmitOutput

    async def invoke(self, payload: BaseModel, context: ToolContext) -> BaseModel:
        assert isinstance(payload, FormSubmitInput)
        user_id, task_id = require_browser_user(context)
        data = await run_browser(
            service().submit_form(
                session_id=payload.session_id,
                user_id=user_id,
                task_id=task_id,
                selector=payload.selector,
            )
        )
        return FormSubmitOutput(**data)


def all_browser_tools() -> list[BaseTool]:
    return [
        BrowserSessionCreateTool(),
        BrowserSessionCloseTool(),
        BrowserNavigateTool(),
        BrowserTitleTool(),
        BrowserTextTool(),
        BrowserScreenshotTool(),
        BrowserInspectTool(),
        BrowserClickTool(),
        BrowserTypeTool(),
        BrowserScrollTool(),
        BrowserWaitTool(),
        BrowserFormFillTool(),
        BrowserFormSubmitTool(),
    ]