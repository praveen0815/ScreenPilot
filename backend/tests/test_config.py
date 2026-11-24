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
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
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


def test_apply_compose_database_url_encodes_special_characters():
    from app.core.database_url import apply_compose_database_url

    env = {
        "POSTGRES_HOST": "postgres",
        "POSTGRES_USER": "screenpilot",
        "POSTGRES_PASSWORD": "p@ss:word/x",
        "POSTGRES_DB": "screenpilot",
        "DATABASE_URL": "postgresql+asyncpg://screenpilot:broken@postgres:5432/screenpilot",
    }

    url = apply_compose_database_url(env)

    assert url == (
        "postgresql+asyncpg://screenpilot:p%40ss%3Aword%2Fx@postgres:5432/screenpilot"
    )
    assert env["DATABASE_URL"] == url


def test_settings_use_encoded_url_after_compose_apply(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://screenpilot:broken@postgres:5432/screenpilot",
    )
    monkeypatch.setenv("POSTGRES_HOST", "postgres")
    monkeypatch.setenv("POSTGRES_USER", "screenpilot")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:word/x")
    monkeypatch.setenv("POSTGRES_DB", "screenpilot")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:9/0")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-with-32-characters-minimum")
    monkeypatch.setenv("APP_ENV", "test")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.database_url == (
        "postgresql+asyncpg://screenpilot:p%40ss%3Aword%2Fx@postgres:5432/screenpilot"
    )


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
