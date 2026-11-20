"""add fan art system

Revision ID: 7f8e9a0b1c2d
Revises: 5230e4eca04f
"""

from alembic import op
import sqlalchemy as sa


revision = "7f8e9a0b1c2d"
down_revision = "5230e4eca04f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fan_arts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("image_file_id", sa.String(255), nullable=False),
        sa.Column("rarity", sa.String(30), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_limited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stock", sa.Integer(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_index(
        "ix_fan_arts_rarity",
        "fan_arts",
        ["rarity"],
    )

    op.create_table(
        "fan_art_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_code", sa.String(40), nullable=False, unique=True),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("fan_art_id", sa.Integer(), nullable=False),
        sa.Column("price_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("receipt_file_id", sa.String(255), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fan_art_id"],
            ["fan_arts.id"],
        ),
    )

    op.create_index(
        "ix_fan_art_orders_order_code",
        "fan_art_orders",
        ["order_code"],
        unique=True,
    )

    op.create_index(
        "ix_fan_art_orders_telegram_id",
        "fan_art_orders",
        ["telegram_id"],
    )

    op.create_index(
        "ix_fan_art_orders_status",
        "fan_art_orders",
        ["status"],
    )

    op.create_table(
        "fan_art_ownerships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("fan_art_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("acquired_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fan_art_id"],
            ["fan_arts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["fan_art_orders.id"],
        ),
    )

    op.create_index(
        "ix_fan_art_ownerships_telegram_id",
        "fan_art_ownerships",
        ["telegram_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fan_art_ownerships_telegram_id",
        table_name="fan_art_ownerships",
    )
    op.drop_table("fan_art_ownerships")

    op.drop_index(
        "ix_fan_art_orders_status",
        table_name="fan_art_orders",
    )
    op.drop_index(
        "ix_fan_art_orders_telegram_id",
        table_name="fan_art_orders",
    )
    op.drop_index(
        "ix_fan_art_orders_order_code",
        table_name="fan_art_orders",
    )
    op.drop_table("fan_art_orders")

    op.drop_index(
        "ix_fan_arts_rarity",
        table_name="fan_arts",
    )
    op.drop_table("fan_arts")