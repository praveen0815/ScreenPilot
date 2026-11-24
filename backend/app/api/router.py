from fastapi import APIRouter

from app.api.routes.agent import router as agent_router
from app.api.routes.auth import router as auth_router
from app.api.routes.capabilities import router as capabilities_router
from app.api.routes.health import router as health_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.tools import router as tools_router
from app.api.routes.desktop_control import router as desktop_control_router
from app.api.routes.memory import router as memory_router
from app.api.routes.users import router as users_router
from app.api.routes.events import router as events_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(capabilities_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(tasks_router)
api_router.include_router(agent_router)
api_router.include_router(tools_router)
api_router.include_router(desktop_control_router)
api_router.include_router(memory_router)
api_router.include_router(events_router)
