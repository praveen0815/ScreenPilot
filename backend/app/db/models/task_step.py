import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import StepStatus
from app.db.mixins import TimestampMixin


class TaskStep(TimestampMixin, Base):
    __tablename__ = "task_steps"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    arguments_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[StepStatus] = mapped_column(
        String(20),
        default=StepStatus.PLANNED,
        server_default=StepStatus.PLANNED.value,
        nullable=False,
    )

    task: Mapped["AgentTask"] = relationship(back_populates="steps")
    tool_executions: Mapped[list["ToolExecution"]] = relationship(back_populates="step")