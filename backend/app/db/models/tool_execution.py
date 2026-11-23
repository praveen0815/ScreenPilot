import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import ToolExecutionStatus


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("task_steps.id", ondelete="SET NULL"), index=True, nullable=True
    )
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[ToolExecutionStatus] = mapped_column(
        String(20),
        default=ToolExecutionStatus.PENDING,
        server_default=ToolExecutionStatus.PENDING.value,
        nullable=False,
    )
    arguments_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task: Mapped["AgentTask"] = relationship(back_populates="tool_executions")
    step: Mapped["TaskStep | None"] = relationship(back_populates="tool_executions")