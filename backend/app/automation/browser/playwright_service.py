import asyncio
import base64
import logging
from uuid import UUID

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from app.automation.browser.errors import (
    BrowserActionError,
    BrowserAutomationError,
    BrowserDisabledError,
    BrowserSessionDisconnectedError,
)
from app.automation.browser.session_manager import BrowserRuntime, BrowserSessionManager, OwnedBrowserSession
from app.automation.browser.url_policy import validate_css_selector, validate_navigation_url
from app.core.config import Settings, get_settings

logger = logging.getLogger("app.browser.playwright")

_manager = BrowserSessionManager()
_lock = asyncio.Lock()
_started = False


def get_browser_session_manager() -> BrowserSessionManager:
    return _manager


class BrowserAutomationService:
    """Playwright-backed Chromium automation with per-task session ownership."""

    name = "browser"
    detail = "Chromium browser automation via Playwright with validated URLs and scoped sessions."

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def availability(self) -> str:
        return "available" if self._settings.browser_enabled else "unavailable"

    async def ensure_started(self) -> None:
        global _started
        if not self._settings.browser_enabled:
            raise BrowserDisabledError("Browser automation is disabled.")
        if _started and _manager.runtime is not None:
            return
        async with _lock:
            if _started and _manager.runtime is not None:
                return
            playwright = await async_playwright().start()
            launch_kwargs: dict = {"headless": self._settings.browser_headless}
            if self._settings.browser_chromium_executable:
                launch_kwargs["executable_path"] = self._settings.browser_chromium_executable
            try:
                browser = await playwright.chromium.launch(**launch_kwargs)
            except PlaywrightError as exc:
                await playwright.stop()
                raise BrowserActionError(f"Failed to launch Chromium: {exc}") from exc
            _manager.attach_runtime(BrowserRuntime(playwright=playwright, browser=browser))
            _started = True
            logger.info("browser_runtime_started")

    async def shutdown(self) -> None:
        global _started
        async with _lock:
            await _manager.shutdown()
            runtime = _manager.runtime
            if runtime is not None:
                try:
                    await runtime.browser.close()
                except Exception:
                    logger.exception("browser_shutdown_close_failed")
                try:
                    await runtime.playwright.stop()
                except Exception:
                    logger.exception("browser_shutdown_playwright_stop_failed")
            _manager.clear_runtime()
            _started = False

    def _require_session(self, session_id: UUID, *, user_id: UUID, task_id: UUID) -> OwnedBrowserSession:
        try:
            return _manager.get_session(session_id, user_id=user_id, task_id=task_id)
        except BrowserAutomationError:
            raise
        except Exception as exc:
            raise BrowserSessionDisconnectedError("Browser session is unavailable.") from exc

    async def create_session(self, *, user_id: UUID, task_id: UUID) -> UUID:
        await self.ensure_started()
        session = await _manager.create_session(user_id=user_id, task_id=task_id)
        return session.session_id

    async def close_session(self, *, session_id: UUID, user_id: UUID, task_id: UUID) -> int:
        await self.ensure_started()
        return await _manager.close_session(session_id, user_id=user_id, task_id=task_id)

    async def navigate(self, *, session_id: UUID, user_id: UUID, task_id: UUID, url: str) -> dict[str, str]:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        safe_url = validate_navigation_url(url, self._settings)
        timeout = self._settings.browser_navigation_timeout_ms
        try:
            response = await session.page.goto(
                safe_url,
                wait_until="domcontentloaded",
                timeout=timeout,
            )
            final_url = session.page.url
            title = await session.page.title()
        except PlaywrightError as exc:
            session.record("navigate", success=False, detail=str(exc))
            session.connected = False
            raise BrowserActionError("Navigation failed.") from exc
        status = str(response.status) if response is not None else "unknown"
        session.record("navigate", success=True, detail=f"{status} {final_url}")
        return {"url": final_url, "title": title[:500]}

    async def get_title(self, *, session_id: UUID, user_id: UUID, task_id: UUID) -> str:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        try:
            title = await session.page.title()
        except PlaywrightError as exc:
            session.connected = False
            raise BrowserActionError("Could not read page title.") from exc
        session.record("title", success=True, detail=title[:120])
        return title[:500]

    async def get_visible_text(self, *, session_id: UUID, user_id: UUID, task_id: UUID) -> str:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        try:
            text = await session.page.locator("body").inner_text()
        except PlaywrightError as exc:
            session.connected = False
            raise BrowserActionError("Could not read page text.") from exc
        clipped = text.strip()[: self._settings.browser_max_text_chars]
        session.record("text", success=True, detail=f"{len(clipped)} chars")
        return clipped

    async def screenshot(self, *, session_id: UUID, user_id: UUID, task_id: UUID) -> dict[str, str | int]:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        try:
            raw = await session.page.screenshot(type="png", full_page=False)
        except PlaywrightError as exc:
            session.connected = False
            raise BrowserActionError("Screenshot failed.") from exc
        if len(raw) > self._settings.browser_max_screenshot_bytes:
            raise BrowserActionError("Screenshot exceeds the configured size limit.")
        encoded = base64.b64encode(raw).decode("ascii")
        session.record("screenshot", success=True, detail=f"{len(raw)} bytes")
        return {"image_base64": encoded, "byte_length": len(raw), "format": "png"}

    async def inspect_element(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        task_id: UUID,
        selector: str,
    ) -> dict[str, str | bool | int | None]:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        css = validate_css_selector(selector)
        locator = session.page.locator(css).first
        timeout = self._settings.browser_action_timeout_ms
        try:
            await locator.wait_for(state="attached", timeout=timeout)
            tag = await locator.evaluate("element => element.tagName.toLowerCase()")
            text = (await locator.inner_text())[:500]
            visible = await locator.is_visible()
            box = await locator.bounding_box()
        except PlaywrightError as exc:
            session.record("inspect", success=False, detail=str(exc))
            raise BrowserActionError("Element inspection failed.") from exc
        height = int(box["height"]) if box else None
        width = int(box["width"]) if box else None
        session.record("inspect", success=True, detail=f"{tag} {css}")
        return {
            "selector": css,
            "tag": str(tag),
            "text": text.strip(),
            "visible": visible,
            "height": height,
            "width": width,
        }

    async def click(self, *, session_id: UUID, user_id: UUID, task_id: UUID, selector: str) -> dict[str, str]:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        css = validate_css_selector(selector)
        timeout = self._settings.browser_action_timeout_ms
        try:
            await session.page.locator(css).first.click(timeout=timeout)
            url = session.page.url
        except PlaywrightError as exc:
            session.record("click", success=False, detail=str(exc))
            raise BrowserActionError("Click failed.") from exc
        session.record("click", success=True, detail=css)
        return {"url": url[:500]}

    async def type_text(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        task_id: UUID,
        selector: str,
        text: str,
        clear_first: bool = True,
    ) -> dict[str, bool]:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        css = validate_css_selector(selector)
        if len(text) > 2000:
            raise BrowserActionError("Text exceeds 2000 characters.")
        locator = session.page.locator(css).first
        timeout = self._settings.browser_action_timeout_ms
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            if clear_first:
                await locator.fill(text, timeout=timeout)
            else:
                await locator.type(text, timeout=timeout)
        except PlaywrightError as exc:
            session.record("type", success=False, detail=str(exc))
            raise BrowserActionError("Typing failed.") from exc
        session.record("type", success=True, detail=css)
        return {"typed": True}

    async def scroll(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        task_id: UUID,
        delta_y: int,
        selector: str | None = None,
    ) -> dict[str, bool]:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        try:
            if selector:
                css = validate_css_selector(selector)
                await session.page.locator(css).first.scroll_into_view_if_needed(
                    timeout=self._settings.browser_action_timeout_ms
                )
            else:
                await session.page.mouse.wheel(0, delta_y)
        except PlaywrightError as exc:
            session.record("scroll", success=False, detail=str(exc))
            raise BrowserActionError("Scroll failed.") from exc
        session.record("scroll", success=True, detail=selector or f"delta_y={delta_y}")
        return {"scrolled": True}

    async def wait_for_element(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        task_id: UUID,
        selector: str,
        state: str,
        timeout_ms: int,
    ) -> dict[str, bool]:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        css = validate_css_selector(selector)
        capped = min(max(timeout_ms, 100), self._settings.browser_wait_max_timeout_ms)
        allowed = {"attached", "detached", "visible", "hidden"}
        if state not in allowed:
            raise BrowserActionError("state must be attached, detached, visible, or hidden.")
        try:
            await session.page.locator(css).first.wait_for(state=state, timeout=capped)
        except PlaywrightError as exc:
            session.record("wait", success=False, detail=str(exc))
            raise BrowserActionError("Wait for element timed out or failed.") from exc
        session.record("wait", success=True, detail=f"{css} {state}")
        return {"ready": True}

    async def fill_form(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        task_id: UUID,
        fields: list[tuple[str, str]],
    ) -> dict[str, int]:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        count = 0
        timeout = self._settings.browser_action_timeout_ms
        for selector, value in fields:
            css = validate_css_selector(selector)
            if len(value) > 2000:
                raise BrowserActionError("Field value exceeds 2000 characters.")
            try:
                await session.page.locator(css).first.fill(value, timeout=timeout)
                count += 1
            except PlaywrightError as exc:
                session.record("form.fill", success=False, detail=str(exc))
                raise BrowserActionError("Form fill failed.") from exc
        session.record("form.fill", success=True, detail=f"{count} fields")
        return {"fields_filled": count}

    async def submit_form(self, *, session_id: UUID, user_id: UUID, task_id: UUID, selector: str) -> dict[str, str]:
        session = self._require_session(session_id, user_id=user_id, task_id=task_id)
        css = validate_css_selector(selector)
        timeout = self._settings.browser_action_timeout_ms
        try:
            await session.page.locator(css).first.click(timeout=timeout)
            await session.page.wait_for_load_state("domcontentloaded", timeout=self._settings.browser_navigation_timeout_ms)
            url = session.page.url
        except PlaywrightError as exc:
            session.record("form.submit", success=False, detail=str(exc))
            raise BrowserActionError("Form submit failed.") from exc
        session.record("form.submit", success=True, detail=css)
        return {"url": url[:500]}


_service: BrowserAutomationService | None = None


def get_browser_automation_service() -> BrowserAutomationService:
    global _service
    if _service is None:
        _service = BrowserAutomationService()
    return _service