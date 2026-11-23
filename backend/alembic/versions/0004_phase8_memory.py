"""Phase 8 — task memory, preferences, and context checkpoints.

Revision ID: 0004_phase8_memory
Revises: 0003_agent_plan_fields
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_phase8_memory"
down_revision: Union[str, Sequence[str], None] = "0003_agent_plan_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_tasks", sa.Column("task_summary", sa.Text(), nullable=True))
    op.add_column("agent_tasks", sa.Column("context_checkpoint_json", sa.Text(), nullable=True))

    op.create_table(
        "task_memory_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_chars", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_memory_expires", "task_memory_entries", ["expires_at"])
    op.create_index("ix_task_memory_entries_task_id", "task_memory_entries", ["task_id"])
    op.create_index("ix_task_memory_entries_user_id", "task_memory_entries", ["user_id"])
    op.create_index("ix_task_memory_user_task", "task_memory_entries", ["user_id", "task_id", "created_at"])

    op.create_table(
        "user_agent_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("preferences_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_agent_preferences")
    op.drop_index("ix_task_memory_user_task", table_name="task_memory_entries")
    op.drop_index("ix_task_memory_entries_user_id", table_name="task_memory_entries")
    op.drop_index("ix_task_memory_entries_task_id", table_name="task_memory_entries")
    op.drop_index("ix_task_memory_expires", table_name="task_memory_entries")
    op.drop_table("task_memory_entries")
    op.drop_column("agent_tasks", "context_checkpoint_json")
    op.drop_column("agent_tasks", "task_summary")