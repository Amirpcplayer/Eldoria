"""fix fan art price column types

Revision ID: 4a5b6c7d8e9f
Revises: 3f4a5b6c7d8e
"""

from alembic import op
import sqlalchemy as sa


revision = "4a5b6c7d8e9f"
down_revision = "3f4a5b6c7d8e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "fan_arts",
        "price",
        existing_type=sa.Integer(),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
        postgresql_using="price::numeric(12,2)",
    )

    op.alter_column(
        "fan_art_orders",
        "price_snapshot",
        existing_type=sa.Integer(),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
        postgresql_using="price_snapshot::numeric(12,2)",
    )


def downgrade() -> None:
    op.alter_column(
        "fan_art_orders",
        "price_snapshot",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="price_snapshot::integer",
    )

    op.alter_column(
        "fan_arts",
        "price",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="price::integer",
    )