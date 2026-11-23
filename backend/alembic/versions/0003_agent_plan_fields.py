"""Agent planning fields on tasks and steps.

Revision ID: 0003_agent_plan_fields
Revises: 0002_phase2_auth_and_tasks
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_agent_plan_fields"
down_revision: Union[str, Sequence[str], None] = "0002_phase2_auth_and_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_tasks", sa.Column("intent_json", sa.Text(), nullable=True))
    op.add_column("agent_tasks", sa.Column("plan_json", sa.Text(), nullable=True))
    op.add_column("agent_tasks", sa.Column("outcome_message", sa.Text(), nullable=True))
    op.add_column(
        "agent_tasks",
        sa.Column("cancel_requested", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "agent_tasks",
        sa.Column("pause_requested", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.alter_column("agent_tasks", "status", type_=sa.String(length=32))

    op.add_column("task_steps", sa.Column("tool_name", sa.String(length=120), nullable=True))
    op.add_column("task_steps", sa.Column("arguments_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("task_steps", "arguments_json")
    op.drop_column("task_steps", "tool_name")
    op.drop_column("agent_tasks", "pause_requested")
    op.drop_column("agent_tasks", "cancel_requested")
    op.drop_column("agent_tasks", "outcome_message")
    op.drop_column("agent_tasks", "plan_json")
    op.drop_column("agent_tasks", "intent_json")
    op.alter_column("agent_tasks", "status", type_=sa.String(length=20))