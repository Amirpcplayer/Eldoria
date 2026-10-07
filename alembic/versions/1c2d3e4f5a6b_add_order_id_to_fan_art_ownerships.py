"""add order_id to fan art ownerships

Revision ID: 1c2d3e4f5a6b
Revises: 9b0c1d2e3f4a
"""

from alembic import op
import sqlalchemy as sa


revision = "1c2d3e4f5a6b"
down_revision = "9b0c1d2e3f4a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("fan_art_ownerships")
    }

    if "order_id" not in columns:
        op.add_column(
            "fan_art_ownerships",
            sa.Column(
                "order_id",
                sa.Integer(),
                nullable=True,
            ),
        )

    foreign_keys = inspector.get_foreign_keys("fan_art_ownerships")

    has_order_fk = any(
        "order_id" in (foreign_key.get("constrained_columns") or [])
        for foreign_key in foreign_keys
    )

    if not has_order_fk:
        op.create_foreign_key(
            "fk_fan_art_ownerships_order_id",
            "fan_art_ownerships",
            "fan_art_orders",
            ["order_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    foreign_keys = inspector.get_foreign_keys("fan_art_ownerships")

    for foreign_key in foreign_keys:
        constrained_columns = foreign_key.get("constrained_columns") or []

        if "order_id" in constrained_columns:
            constraint_name = foreign_key.get("name")

            if constraint_name:
                op.drop_constraint(
                    constraint_name,
                    "fan_art_ownerships",
                    type_="foreignkey",
                )

    columns = {
        column["name"]
        for column in inspector.get_columns("fan_art_ownerships")
    }

    if "order_id" in columns:
        op.drop_column(
            "fan_art_ownerships",
            "order_id",
        )