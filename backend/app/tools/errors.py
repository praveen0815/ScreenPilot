class ToolError(Exception):
    """Base class for tool-layer failures."""

    code: str = "tool_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ToolValidationError(ToolError):
    code = "tool_validation_error"


class ToolPermissionError(ToolError):
    code = "tool_permission_denied"


class ToolTimeoutError(ToolError):
    code = "tool_timeout"