"""Phase 10 — workflow execution state persistence.

Revision ID: 0006_phase10_workflow
Revises: 0005_phase9_safety_approvals
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_phase10_workflow"
down_revision: Union[str, Sequence[str], None] = "0005_phase9_safety_approvals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_tasks", sa.Column("workflow_state_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_tasks", "workflow_state_json")