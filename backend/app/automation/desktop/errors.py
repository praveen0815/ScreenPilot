class DesktopAutomationError(Exception):
    code: str = "desktop_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DesktopDisabledError(DesktopAutomationError):
    code = "desktop_disabled"


class DesktopBoundsError(DesktopAutomationError):
    code = "desktop_bounds_error"


class DesktopHotkeyDeniedError(DesktopAutomationError):
    code = "desktop_hotkey_denied"


class DesktopEmergencyStopError(DesktopAutomationError):
    code = "desktop_emergency_stop"


class DesktopActionCancelledError(DesktopAutomationError):
    code = "desktop_action_cancelled"


class DesktopActionError(DesktopAutomationError):
    code = "desktop_action_failed"