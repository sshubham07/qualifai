"""interviews can be submitted without an email, so without a user

Revision ID: a4f2c8d16e73
Revises: 7c1e5a9d2b40
Create Date: 2026-10-11 23:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "a4f2c8d16e73"
down_revision = "7c1e5a9d2b40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("interviews", "user_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    # Fails while interviews without a user exist: there is no user to give them.
    op.alter_column("interviews", "user_id", existing_type=sa.Uuid(), nullable=False)
