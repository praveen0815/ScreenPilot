import asyncio
import logging

from redis.asyncio import Redis
from sqlalchemy import text

from app.db.session import get_engine
from app.schemas.system import CheckResult

logger = logging.getLogger(__name__)


async def check_database(timeout_seconds: float) -> CheckResult:
    engine = get_engine()
    try:
        async with asyncio.timeout(timeout_seconds):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        return CheckResult(status="up")
    except Exception as exc:
        logger.warning("database check failed: %s", type(exc).__name__)
        return CheckResult(status="down", detail=type(exc).__name__)


async def check_redis(redis_url: str, timeout_seconds: float) -> CheckResult:
    client = Redis.from_url(
        redis_url,
        socket_connect_timeout=timeout_seconds,
        socket_timeout=timeout_seconds,
    )
    try:
        async with asyncio.timeout(timeout_seconds):
            await client.ping()
        return CheckResult(status="up")
    except Exception as exc:
        logger.warning("redis check failed: %s", type(exc).__name__)
        return CheckResult(status="down", detail=type(exc).__name__)
    finally:
        await client.aclose()
