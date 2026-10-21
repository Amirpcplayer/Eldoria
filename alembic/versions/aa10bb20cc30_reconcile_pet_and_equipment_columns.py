"""Safely reconcile columns required by pet training and gem equipment."""
from alembic import op
import sqlalchemy as sa

revision = "aa10bb20cc30"
down_revision = "f8a1c2d3e4b5"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    # Idempotent checks also repair databases whose Alembic version was stamped
    # ahead of the actual schema. Existing player data is preserved.
    pet_columns = _columns("character_pets")
    if pet_columns and "last_training_at" not in pet_columns:
        op.add_column(
            "character_pets",
            sa.Column("last_training_at", sa.DateTime(), nullable=True),
        )

    equipment_columns = _columns("equipments")
    added_gem_price = bool(equipment_columns and "gem_price" not in equipment_columns)
    if added_gem_price:
        op.add_column(
            "equipments",
            sa.Column(
                "gem_price", sa.Integer(), nullable=False, server_default="0"
            ),
        )

    if equipment_columns:
        indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("equipments")}
        if "ix_equipments_gem_price" not in indexes:
            op.create_index(
                "ix_equipments_gem_price", "equipments", ["gem_price"], unique=False
            )


def downgrade() -> None:
    # Deliberately do not drop compatibility columns: they may have been
    # present before this revision and contain live player state.
    pass
