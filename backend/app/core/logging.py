import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
task_id_var: ContextVar[str | None] = ContextVar("task_id", default=None)
agent_execution_id_var: ContextVar[str | None] = ContextVar("agent_execution_id", default=None)
tool_execution_id_var: ContextVar[str | None] = ContextVar("tool_execution_id", default=None)


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        for key in (
            "request_id",
            "task_id",
            "agent_execution_id",
            "tool_execution_id",
            "event_id",
            "event_type",
            "sequence",
            "user_id",
            "duration_ms",
            "http_method",
            "http_path",
            "http_status",
        ):
            value = getattr(record, key, None)
            if value is None and key == "request_id":
                value = request_id_var.get()
            elif value is None and key == "task_id":
                value = task_id_var.get()
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
