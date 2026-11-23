import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import __version__
from app.core.config import get_settings
from app.db.checks import check_database, check_redis
from app.schemas.system import HealthResponse, ReadyResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, version=__version__)


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={503: {"model": ReadyResponse}},
)
async def ready() -> JSONResponse:
    settings = get_settings()
    timeout = settings.dependency_check_timeout_seconds
    database, redis = await asyncio.gather(
        check_database(timeout),
        check_redis(settings.redis_url, timeout),
    )
    checks = {"database": database, "redis": redis}
    is_ready = all(item.status == "up" for item in checks.values())
    body = ReadyResponse(status="ready" if is_ready else "not_ready", checks=checks)
    return JSONResponse(status_code=200 if is_ready else 503, content=body.model_dump())
