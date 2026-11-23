import logging

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import JsonFormatter


def test_settings_require_jwt_secret(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://screenpilot:screenpilot@127.0.0.1:5432/screenpilot",
    )
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:9/0")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_require_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:9/0")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-with-32-characters-minimum")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_non_async_database_driver(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://screenpilot:screenpilot@127.0.0.1:5432/screenpilot")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:9/0")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-with-32-characters-minimum")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_non_redis_url(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://screenpilot:screenpilot@127.0.0.1:5432/screenpilot",
    )
    monkeypatch.setenv("REDIS_URL", "http://127.0.0.1:6379/0")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-with-32-characters-minimum")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_short_jwt_secret_outside_test(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://screenpilot:screenpilot@127.0.0.1:5432/screenpilot",
    )
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:9/0")
    monkeypatch.setenv("JWT_SECRET", "too-short")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_json_formatter_emits_message_without_extra_secrets():
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="database check failed: %s",
        args=("ConnectionRefusedError",),
        exc_info=None,
    )

    payload = JsonFormatter().format(record)

    assert '"message": "database check failed: ConnectionRefusedError"' in payload
    assert "postgresql" not in payload
