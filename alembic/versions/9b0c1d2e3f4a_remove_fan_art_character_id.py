"""remove obsolete character_id from fan art orders

Revision ID: 9b0c1d2e3f4a
Revises: 8a9b0c1d2e3f
"""

from alembic import op
import sqlalchemy as sa


revision = "9b0c1d2e3f4a"
down_revision = "8a9b0c1d2e3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("fan_art_orders")
    }

    if "character_id" not in columns:
        return

    foreign_keys = inspector.get_foreign_keys("fan_art_orders")

    for foreign_key in foreign_keys:
        constrained_columns = foreign_key.get("constrained_columns") or []

        if "character_id" in constrained_columns:
            constraint_name = foreign_key.get("name")

            if constraint_name:
                op.drop_constraint(
                    constraint_name,
                    "fan_art_orders",
                    type_="foreignkey",
                )

    indexes = inspector.get_indexes("fan_art_orders")

    for index in indexes:
        index_columns = index.get("column_names") or []

        if "character_id" in index_columns:
            index_name = index.get("name")

            if index_name:
                op.drop_index(
                    index_name,
                    table_name="fan_art_orders",
                )

    op.drop_column(
        "fan_art_orders",
        "character_id",
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("fan_art_orders")
    }

    if "character_id" in columns:
        return

    op.add_column(
        "fan_art_orders",
        sa.Column(
            "character_id",
            sa.Integer(),
            nullable=True,
        ),
    )