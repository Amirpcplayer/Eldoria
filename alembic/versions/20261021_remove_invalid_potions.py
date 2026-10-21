"""Retire unsupported potion variants and remove them from every inventory.

Only the four canonical small/large HP and Mana potions remain available.
Legacy catalog rows are retained as retired records to avoid breaking historical
foreign-key references, but are hidden from the game's potion systems.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261021_remove_invalid_potions"
down_revision: Union[str, Sequence[str], None] = "51efc7a86442"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VALID_POTIONS = (
    "🧪 معجون سلامتی",
    "🧪 معجون سلامتی بزرگ",
    "🔷 معجون مانا",
    "🧪 معجون مانای بزرگ",
)


def upgrade() -> None:
    conn = op.get_bind()
    # Identify unsupported potion-like catalog rows. Exact valid names are preserved.
    invalid_ids = sa.text("""
        SELECT id
        FROM items
        WHERE (
            item_type = 'potion'
            OR name ILIKE '%معجون%'
            OR name ILIKE '%potion%'
        )
        AND name NOT IN (:hp_small, :hp_large, :mana_small, :mana_large)
    """)
    params = {
        "hp_small": VALID_POTIONS[0],
        "hp_large": VALID_POTIONS[1],
        "mana_small": VALID_POTIONS[2],
        "mana_large": VALID_POTIONS[3],
    }
    rows = conn.execute(invalid_ids, params).fetchall()
    ids = [row[0] for row in rows]
    if not ids:
        return

    # Remove all player holdings first, then retire catalog rows without deleting
    # records that might be referenced by recipes or historical transactions.
    conn.execute(
        sa.text("DELETE FROM inventories WHERE item_id = ANY(:item_ids)"),
        {"item_ids": ids},
    )
    conn.execute(
        sa.text("""
            UPDATE items
            SET item_type = 'retired_potion',
                buy_price = 0,
                sell_price = 0,
                is_tradeable = FALSE
            WHERE id = ANY(:item_ids)
        """),
        {"item_ids": ids},
    )


def downgrade() -> None:
    # Removed player quantities cannot be reconstructed safely.
    # Do not reintroduce unsupported potions automatically.
    pass
