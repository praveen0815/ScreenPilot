import asyncio
import logging
from collections import defaultdict
from uuid import UUID

from app.events.schemas import TaskEventWire

logger = logging.getLogger("app.events.broker")


class TaskEventBroker:
    """In-process fan-out for task events (single worker)."""

    def __init__(self) -> None:
        self._queues: dict[UUID, set[asyncio.Queue[TaskEventWire]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, user_id: UUID) -> asyncio.Queue[TaskEventWire]:
        queue: asyncio.Queue[TaskEventWire] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._queues[user_id].add(queue)
        return queue

    async def unsubscribe(self, user_id: UUID, queue: asyncio.Queue[TaskEventWire]) -> None:
        async with self._lock:
            user_queues = self._queues.get(user_id)
            if user_queues is None:
                return
            user_queues.discard(queue)
            if not user_queues:
                self._queues.pop(user_id, None)

    async def publish(self, user_id: UUID, event: TaskEventWire) -> None:
        async with self._lock:
            targets = list(self._queues.get(user_id, set()))
        for queue in targets:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "event_subscriber_queue_full",
                    extra={"user_id": str(user_id), "task_id": str(event.task_id), "event_type": event.type},
                )


_broker = TaskEventBroker()


def get_task_event_broker() -> TaskEventBroker:
    return _broker