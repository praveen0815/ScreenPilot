import logging

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.errors")


class AppError(Exception):
    """Expected application failure with a stable client-facing code."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AgentUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="agent_unavailable",
            message="The agent runtime is not enabled in this build.",
            status_code=501,
        )


class AutomationUnavailableError(AppError):
    def __init__(self, engine: str) -> None:
        super().__init__(
            code="automation_unavailable",
            message=f"The {engine} automation engine is not enabled in this build.",
            status_code=501,
        )


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication required or invalid.") -> None:
        super().__init__(code="authentication_error", message=message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have access to this resource.") -> None:
        super().__init__(code="forbidden", message=message, status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(code="conflict", message=message, status_code=409)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(code="not_found", message=message, status_code=404)


class UnknownToolError(AppError):
    def __init__(self, name: str) -> None:
        super().__init__(
            code="unknown_tool",
            message=f"No tool named '{name}' is registered.",
            status_code=404,
        )


def error_body(code: str, message: str, details: object | None = None) -> dict[str, object]:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                "validation_error",
                "Request validation failed.",
                jsonable_encoder(exc.errors()),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(status_code=exc.status_code, content=error_body("http_error", message))

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled error: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "An unexpected error occurred."),
        )
