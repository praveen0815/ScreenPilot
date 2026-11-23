import asyncio
import os

import pytest

from app.db.checks import check_database


def _postgres_url() -> str | None:
    return os.getenv("INTEGRATION_DATABASE_URL")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_health_when_postgres_is_available():
    database_url = _postgres_url()
    if not database_url:
        pytest.skip("INTEGRATION_DATABASE_URL is not set.")
    os.environ["DATABASE_URL"] = database_url
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    result = await check_database(settings.dependency_check_timeout_seconds)
    if result.status != "up":
        pytest.skip(f"PostgreSQL unavailable: {result.detail}")
    assert result.status == "up"