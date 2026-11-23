import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "test"
os.environ["APP_NAME"] = "ScreenPilot"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://screenpilot:screenpilot@127.0.0.1:9/screenpilot"
os.environ["REDIS_URL"] = "redis://127.0.0.1:9/0"
os.environ["DEPENDENCY_CHECK_TIMEOUT_SECONDS"] = "1"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["JWT_SECRET"] = "test-jwt-secret-with-32-characters-minimum"

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import configure_engine, dispose_engine, get_engine
from app.main import create_app

get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
async def sqlite_app_client():
    get_settings.cache_clear()
    configure_engine("sqlite+aiosqlite:///:memory:")
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    with TestClient(create_app()) as test_client:
        yield test_client
    await dispose_engine()
    get_settings.cache_clear()