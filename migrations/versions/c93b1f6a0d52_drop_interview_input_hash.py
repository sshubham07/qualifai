"""every submission is a new interview: the input hash used to reuse kits is gone

Revision ID: c93b1f6a0d52
Revises: a4f2c8d16e73
Create Date: 2026-10-12 12:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "c93b1f6a0d52"
down_revision = "a4f2c8d16e73"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f("ix_interviews_input_hash"), table_name="interviews")
    op.drop_column("interviews", "input_hash")


def downgrade() -> None:
    # The hashes cannot be recomputed here; existing rows get an empty one and are never matched.
    op.add_column(
        "interviews",
        sa.Column("input_hash", sa.String(length=64), nullable=False, server_default=""),
    )
    op.alter_column("interviews", "input_hash", server_default=None)
    op.create_index(op.f("ix_interviews_input_hash"), "interviews", ["input_hash"], unique=False)
