"""Remove the obsolete player language preference.

Language switching is no longer supported. The game uses Persian as its fixed
language, so the player_settings.language column is no longer needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "remove_player_language_20261022"
down_revision: Union[str, Sequence[str], None] = (
    "20261021_remove_invalid_potions",
    "guild_material_sales_20261021",
    "guild_inventory_sales_20261019",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "player_settings" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("player_settings")}
    if "language" in columns:
        op.drop_column("player_settings", "language")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "player_settings" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("player_settings")}
    if "language" not in columns:
        op.add_column(
            "player_settings",
            sa.Column("language", sa.String(length=8), nullable=False, server_default="fa"),
        )
