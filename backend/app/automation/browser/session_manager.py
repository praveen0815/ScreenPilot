import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from playwright.async_api import Browser, BrowserContext, Page, Playwright

from app.automation.browser.errors import (
    BrowserSessionDisconnectedError,
    BrowserSessionNotFoundError,
    BrowserSessionOwnershipError,
)

logger = logging.getLogger("app.browser.session")


@dataclass
class BrowserActionRecord:
    action: str
    success: bool
    detail: str
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OwnedBrowserSession:
    session_id: UUID
    user_id: UUID
    task_id: UUID
    context: BrowserContext
    page: Page
    connected: bool = True
    action_log: list[BrowserActionRecord] = field(default_factory=list)

    def record(self, action: str, *, success: bool, detail: str) -> None:
        self.action_log.append(BrowserActionRecord(action=action, success=success, detail=detail))
        logger.info(
            "browser_action",
            extra={
                "session_id": str(self.session_id),
                "action": action,
                "success": success,
                "detail": detail[:200],
            },
        )


@dataclass
class BrowserRuntime:
    playwright: Playwright
    browser: Browser


class BrowserSessionManager:
    def __init__(self) -> None:
        self._runtime: BrowserRuntime | None = None
        self._sessions: dict[UUID, OwnedBrowserSession] = {}

    @property
    def runtime(self) -> BrowserRuntime | None:
        return self._runtime

    def attach_runtime(self, runtime: BrowserRuntime) -> None:
        self._runtime = runtime

    def clear_runtime(self) -> None:
        self._runtime = None
        self._sessions.clear()

    async def create_session(self, *, user_id: UUID, task_id: UUID) -> OwnedBrowserSession:
        if self._runtime is None:
            raise BrowserSessionDisconnectedError("Browser runtime is not running.")
        context = await self._runtime.browser.new_context(
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
        )
        page = await context.new_page()
        session_id = uuid4()
        session = OwnedBrowserSession(
            session_id=session_id,
            user_id=user_id,
            task_id=task_id,
            context=context,
            page=page,
        )
        self._sessions[session_id] = session
        session.record("session.create", success=True, detail="Session created.")
        return session

    def get_session(self, session_id: UUID, *, user_id: UUID, task_id: UUID) -> OwnedBrowserSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise BrowserSessionNotFoundError("Browser session not found.")
        if session.user_id != user_id or session.task_id != task_id:
            raise BrowserSessionOwnershipError("Browser session is not owned by this task.")
        if not session.connected:
            raise BrowserSessionDisconnectedError("Browser session is disconnected.")
        if session.page.is_closed():
            session.connected = False
            raise BrowserSessionDisconnectedError("Browser page is closed.")
        return session

    async def close_session(self, session_id: UUID, *, user_id: UUID, task_id: UUID) -> int:
        session = self._sessions.get(session_id)
        if session is None:
            raise BrowserSessionNotFoundError("Browser session not found.")
        if session.user_id != user_id or session.task_id != task_id:
            raise BrowserSessionOwnershipError("Browser session is not owned by this task.")
        session.record("session.close", success=True, detail="Session closing.")
        if session.connected:
            try:
                await session.context.close()
            except Exception:
                logger.exception("browser_session_close_failed", extra={"session_id": str(session_id)})
            session.connected = False
        action_count = len(session.action_log)
        del self._sessions[session_id]
        return action_count

    async def shutdown(self) -> None:
        for session in list(self._sessions.values()):
            if session.connected:
                try:
                    await session.context.close()
                except Exception:
                    logger.exception("browser_session_close_failed", extra={"session_id": str(session.session_id)})
                session.connected = False
        self._sessions.clear()