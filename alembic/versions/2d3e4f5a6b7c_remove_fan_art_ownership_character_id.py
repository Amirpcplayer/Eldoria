"""remove obsolete character_id from fan art ownerships

Revision ID: 2d3e4f5a6b7c
Revises: 1c2d3e4f5a6b
"""

from alembic import op
import sqlalchemy as sa


revision = "2d3e4f5a6b7c"
down_revision = "1c2d3e4f5a6b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("fan_art_ownerships")
    }

    if "character_id" not in columns:
        return

    # ---------------------------------------------------------
    # Remove foreign keys using character_id
    # ---------------------------------------------------------
    foreign_keys = inspector.get_foreign_keys("fan_art_ownerships")

    for foreign_key in foreign_keys:
        constrained_columns = foreign_key.get("constrained_columns") or []

        if "character_id" in constrained_columns:
            constraint_name = foreign_key.get("name")

            if constraint_name:
                op.drop_constraint(
                    constraint_name,
                    "fan_art_ownerships",
                    type_="foreignkey",
                )

    # ---------------------------------------------------------
    # Remove UNIQUE constraints using character_id
    # ---------------------------------------------------------
    unique_constraints = inspector.get_unique_constraints(
        "fan_art_ownerships"
    )

    for constraint in unique_constraints:
        constraint_columns = constraint.get("column_names") or []

        if "character_id" in constraint_columns:
            constraint_name = constraint.get("name")

            if constraint_name:
                op.drop_constraint(
                    constraint_name,
                    "fan_art_ownerships",
                    type_="unique",
                )

    # ---------------------------------------------------------
    # Remove normal indexes using character_id
    # ---------------------------------------------------------
    indexes = inspector.get_indexes("fan_art_ownerships")

    for index in indexes:
        index_columns = index.get("column_names") or []

        if "character_id" in index_columns:
            index_name = index.get("name")

            if index_name:
                op.drop_index(
                    index_name,
                    table_name="fan_art_ownerships",
                )

    # ---------------------------------------------------------
    # Finally remove obsolete character_id column
    # ---------------------------------------------------------
    op.drop_column(
        "fan_art_ownerships",
        "character_id",
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("fan_art_ownerships")
    }

    if "character_id" in columns:
        return

    op.add_column(
        "fan_art_ownerships",
        sa.Column(
            "character_id",
            sa.Integer(),
            nullable=True,
        ),
    )