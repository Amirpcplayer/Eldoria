"""add telegram username to characters

Revision ID: add_telegram_username
Revises: 4a5b6c7d8e9f
"""

from alembic import op
import sqlalchemy as sa


revision = "add_telegram_username"
down_revision = "4a5b6c7d8e9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column(
            "telegram_username",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_characters_telegram_username",
        "characters",
        ["telegram_username"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_characters_telegram_username",
        table_name="characters",
    )

    op.drop_column(
        "characters",
        "telegram_username",
    )