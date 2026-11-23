from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict

from app.auth.dependencies import get_current_user
from app.automation.desktop.safety import get_desktop_safety_gate
from app.db.models.user import User

router = APIRouter(prefix="/api/desktop", tags=["desktop"])


class EmergencyStopStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emergency_stop_active: bool


@router.post("/emergency-stop", response_model=EmergencyStopStatus, status_code=status.HTTP_200_OK)
async def activate_emergency_stop(
    current_user: Annotated[User, Depends(get_current_user)],
) -> EmergencyStopStatus:
    del current_user
    gate = get_desktop_safety_gate()
    gate.activate_emergency_stop()
    return EmergencyStopStatus(emergency_stop_active=gate.emergency_stop_active)


@router.post("/emergency-stop/clear", response_model=EmergencyStopStatus)
async def clear_emergency_stop(
    current_user: Annotated[User, Depends(get_current_user)],
) -> EmergencyStopStatus:
    del current_user
    gate = get_desktop_safety_gate()
    gate.clear_emergency_stop()
    return EmergencyStopStatus(emergency_stop_active=gate.emergency_stop_active)


@router.post("/tasks/{task_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_desktop_actions_for_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    del current_user
    gate = get_desktop_safety_gate()
    gate.cancel_task(task_id)
    return {"status": "cancelled", "task_id": str(task_id)}