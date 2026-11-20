"""add crafting XP to characters

Revision ID: b7c9d1e3f5a7
Revises: a3d7e9f102bc
Create Date: 2026-10-09
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c9d1e3f5a7"
down_revision = "a3d7e9f102bc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("crafting_xp", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("characters", "crafting_xp", server_default=None)


def downgrade() -> None:
    op.drop_column("characters", "crafting_xp")
