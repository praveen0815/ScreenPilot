import asyncio
import contextlib
import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_task_for_current_user
from app.auth.permissions import can_access_task
from app.auth.tokens import decode_access_token
from app.core.errors import AuthenticationError
from app.db.models.agent_task import AgentTask
from app.db.models.user import User
from app.db.session import get_db_session, get_session_factory
from app.events.broker import get_task_event_broker
from app.events.schemas import TaskEventWire, WsClientMessage, WsServerMessage
from app.events.service import list_task_events

logger = logging.getLogger("app.events.ws")

router = APIRouter(tags=["events"])


@router.get("/api/tasks/{task_id}/events", response_model=list[TaskEventWire])
async def get_task_events(
    task: Annotated[AgentTask, Depends(get_task_for_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[TaskEventWire]:
    return await list_task_events(session, task_id=task.id, after_sequence=after_sequence, limit=limit)


async def _authenticate_ws_token(session: AsyncSession, token: str | None) -> User:
    if not token:
        raise AuthenticationError()
    claims = decode_access_token(token)
    user = await session.scalar(select(User).where(User.id == claims.user_id))
    if user is None or not user.is_active:
        raise AuthenticationError()
    return user


@router.websocket("/api/ws/events")
async def task_events_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    token = websocket.query_params.get("token")
    filter_task_id: UUID | None = None
    raw_task = websocket.query_params.get("task_id")
    if raw_task:
        try:
            filter_task_id = UUID(raw_task)
        except ValueError:
            await websocket.send_json(WsServerMessage(type="error", message="Invalid task_id.").model_dump(mode="json"))
            await websocket.close(code=4400)
            return

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            user = await _authenticate_ws_token(session, token)
        except AuthenticationError:
            await websocket.send_json(
                WsServerMessage(type="error", message="Authentication failed.").model_dump(mode="json")
            )
            await websocket.close(code=4401)
            return

        if filter_task_id is not None:
            task = await session.get(AgentTask, filter_task_id)
            if task is None or not can_access_task(user, task):
                await websocket.send_json(
                    WsServerMessage(type="error", message="Forbidden task subscription.").model_dump(mode="json")
                )
                await websocket.close(code=4403)
                return

        await websocket.send_json(
            WsServerMessage(type="connected", message=f"user={user.id}").model_dump(mode="json")
        )

        if filter_task_id is not None:
            backlog = await list_task_events(session, task_id=filter_task_id, after_sequence=0, limit=200)
            for event in backlog:
                await websocket.send_json(WsServerMessage(type="event", event=event).model_dump(mode="json"))

        broker = get_task_event_broker()
        queue = await broker.subscribe(user.id)

        filter_holder = {"task_id": filter_task_id}

        async def client_reader() -> None:
            while True:
                incoming = await websocket.receive_text()
                try:
                    data = json.loads(incoming)
                    client = WsClientMessage.model_validate(data)
                except (json.JSONDecodeError, ValidationError):
                    await websocket.send_json(
                        WsServerMessage(type="error", message="Invalid client message.").model_dump(mode="json")
                    )
                    continue
                if client.type == "ping":
                    await websocket.send_json(WsServerMessage(type="pong").model_dump(mode="json"))
                elif client.type == "resume" and client.task_id is not None:
                    task_row = await session.get(AgentTask, client.task_id)
                    if task_row is None or not can_access_task(user, task_row):
                        continue
                    replay = await list_task_events(
                        session,
                        task_id=client.task_id,
                        after_sequence=client.last_sequence or 0,
                        limit=200,
                    )
                    for event in replay:
                        current = filter_holder["task_id"]
                        if current is None or event.task_id == current:
                            await websocket.send_json(
                                WsServerMessage(type="event", event=event).model_dump(mode="json")
                            )
                elif client.type == "subscribe" and client.task_id is not None:
                    task_row = await session.get(AgentTask, client.task_id)
                    if task_row is None or not can_access_task(user, task_row):
                        await websocket.send_json(
                            WsServerMessage(type="error", message="Forbidden task subscription.").model_dump(
                                mode="json"
                            )
                        )
                        continue
                    filter_holder["task_id"] = client.task_id

        reader = asyncio.create_task(client_reader())
        try:
            while True:
                event = await queue.get()
                current = filter_holder["task_id"]
                if current is not None and event.task_id != current:
                    continue
                await websocket.send_json(WsServerMessage(type="event", event=event).model_dump(mode="json"))
        except WebSocketDisconnect:
            logger.info("ws_disconnect", extra={"user_id": str(user.id)})
        finally:
            reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reader
            await broker.unsubscribe(user.id, queue)