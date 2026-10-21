"""Limit shop to four potions and set 20%/40% recovery."""
from alembic import op
import sqlalchemy as sa

revision = "f4c8d2e6a901"
down_revision = "a410b5c9d211"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("UPDATE items SET buy_price = 0 WHERE item_type = 'potion' AND name NOT IN ('🧪 معجون سلامتی', '🧪 معجون سلامتی بزرگ', '🔷 معجون مانا', '🧪 معجون مانای بزرگ')"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۲۰٪ از حداکثر HP؛ بیش از ظرفیت باقی‌مانده بازیابی نمی‌شود.', buy_price = 100 WHERE name = '🧪 معجون سلامتی'"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۴۰٪ از حداکثر HP؛ بیش از ظرفیت باقی‌مانده بازیابی نمی‌شود.', buy_price = 250 WHERE name = '🧪 معجون سلامتی بزرگ'"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۲۰٪ از حداکثر Mana؛ بیش از ظرفیت باقی‌مانده بازیابی نمی‌شود.', buy_price = 300 WHERE name = '🔷 معجون مانا'"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون مانای بزرگ', 'بازیابی ۴۰٪ از حداکثر Mana؛ بیش از ظرفیت باقی‌مانده بازیابی نمی‌شود.', 'potion', 'rare', 200, 800, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون مانای بزرگ')"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۴۰٪ از حداکثر Mana؛ بیش از ظرفیت باقی‌مانده بازیابی نمی‌شود.', buy_price = 800 WHERE name = '🧪 معجون مانای بزرگ'"))


def downgrade():
    # Do not re-enable legacy potion tiers; this is intentionally data-safe.
    pass
