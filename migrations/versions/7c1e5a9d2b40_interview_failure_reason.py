"""interview failure reason; support level set by the intake gate

Revision ID: 7c1e5a9d2b40
Revises: 29415683ec56
Create Date: 2026-10-11 21:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '7c1e5a9d2b40'
down_revision = '29415683ec56'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('interviews', sa.Column('failure_code', sa.String(length=32), nullable=True))
    op.add_column('interviews', sa.Column('failure_reason', sa.Text(), nullable=True))
    op.alter_column('interviews', 'support_level', existing_type=sa.String(length=16), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE interviews SET support_level = 'unsupported' WHERE support_level IS NULL")
    op.alter_column('interviews', 'support_level', existing_type=sa.String(length=16), nullable=False)
    op.drop_column('interviews', 'failure_reason')
    op.drop_column('interviews', 'failure_code')
