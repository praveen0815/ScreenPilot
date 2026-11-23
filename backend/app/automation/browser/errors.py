class BrowserAutomationError(Exception):
    code: str = "browser_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class BrowserDisabledError(BrowserAutomationError):
    code = "browser_disabled"


class BrowserSessionNotFoundError(BrowserAutomationError):
    code = "browser_session_not_found"


class BrowserSessionOwnershipError(BrowserAutomationError):
    code = "browser_session_ownership"


class BrowserSessionDisconnectedError(BrowserAutomationError):
    code = "browser_session_disconnected"


class BrowserActionError(BrowserAutomationError):
    code = "browser_action_failed"