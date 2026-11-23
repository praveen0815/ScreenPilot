import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import MemoryEntryKind, MemoryScope
from app.db.mixins import TimestampMixin


class TaskMemoryEntry(TimestampMixin, Base):
    __tablename__ = "task_memory_entries"
    __table_args__ = (
        Index("ix_task_memory_user_task", "user_id", "task_id", "created_at"),
        Index("ix_task_memory_expires", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[MemoryScope] = mapped_column(String(32), nullable=False)
    kind: Mapped[MemoryEntryKind] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_chars: Mapped[int] = mapped_column(nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    task: Mapped["AgentTask"] = relationship(back_populates="memory_entries")