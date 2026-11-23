"""Phase 9 — approval expiration and safety audit fields.

Revision ID: 0005_phase9_safety_approvals
Revises: 0004_phase8_memory
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_phase9_safety_approvals"
down_revision: Union[str, Sequence[str], None] = "0004_phase8_memory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("approval_requests", sa.Column("display_json", sa.Text(), nullable=True))
    op.add_column("approval_requests", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("approval_requests", sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("approval_requests", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.create_index("ix_approval_requests_expires_at", "approval_requests", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_approval_requests_expires_at", table_name="approval_requests")
    op.drop_column("approval_requests", "rejection_reason")
    op.drop_column("approval_requests", "decided_at")
    op.drop_column("approval_requests", "expires_at")
    op.drop_column("approval_requests", "display_json")