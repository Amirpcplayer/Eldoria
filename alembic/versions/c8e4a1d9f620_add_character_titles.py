"""add level-based character titles

Revision ID: c8e4a1d9f620
Revises: b7c9d1e3f5a7
Create Date: 2026-10-09
"""
from alembic import op
import sqlalchemy as sa

revision = "c8e4a1d9f620"
down_revision = "b7c9d1e3f5a7"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("characters", sa.Column("active_title", sa.String(length=100), nullable=True, server_default="شاگرد اِلدوریا"))
    op.add_column("characters", sa.Column("unlocked_titles", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.alter_column("characters", "active_title", server_default=None)
    op.alter_column("characters", "unlocked_titles", server_default=None)

def downgrade() -> None:
    op.drop_column("characters", "unlocked_titles")
    op.drop_column("characters", "active_title")
