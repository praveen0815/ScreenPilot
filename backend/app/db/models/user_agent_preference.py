import uuid

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin


class UserAgentPreference(TimestampMixin, Base):
    __tablename__ = "user_agent_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    preferences_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    user: Mapped["User"] = relationship(back_populates="agent_preferences")