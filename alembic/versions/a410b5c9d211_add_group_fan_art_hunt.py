"""Add persistent per-group fan-art hunt state.

Revision ID: a410b5c9d211
Revises: d91c7f20a6b4
"""
from alembic import op
import sqlalchemy as sa

revision = "a410b5c9d211"
down_revision = "d91c7f20a6b4"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("fan_arts", sa.Column("value_gold", sa.Integer(), nullable=False, server_default="0"))
    op.execute(sa.text("UPDATE fan_arts SET value_gold = CASE rarity WHEN 'common' THEN 1000 WHEN 'rare' THEN 3000 WHEN 'epic' THEN 10000 WHEN 'legendary' THEN 25000 WHEN 'mythic' THEN 50000 ELSE 1000 END WHERE value_gold = 0"))
    # Enforce one copy of each Fan Art per player, even across simultaneous group claims.
    op.execute(sa.text("DELETE FROM fan_art_ownerships a USING fan_art_ownerships b WHERE a.telegram_id = b.telegram_id AND a.fan_art_id = b.fan_art_id AND a.id > b.id"))
    op.create_unique_constraint("uq_fan_art_owner_art", "fan_art_ownerships", ["telegram_id", "fan_art_id"])
    # Seed all new HP/Mana potion tiers and exact crafting materials idempotently.
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون HP کوچک', 'بازیابی ۲۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'common', 25, 120, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون HP کوچک')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون HP متوسط', 'بازیابی ۲۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'uncommon', 50, 250, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون HP متوسط')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون HP بزرگ', 'بازیابی ۴۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'rare', 100, 500, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون HP بزرگ')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون HP ممتاز', 'بازیابی ۴۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'epic', 200, 1000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون HP ممتاز')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون HP افسانه‌ای', 'بازیابی ۴۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'legendary', 400, 2000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون HP افسانه‌ای')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون HP اسطوره‌ای', 'بازیابی ۴۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'mythic', 800, 4000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون HP اسطوره‌ای')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون HP کهن', 'بازیابی ۴۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'divine', 1200, 6000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون HP کهن')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون HP ابدی', 'بازیابی ۴۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'divine', 1800, 9000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون HP ابدی')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون HP قهرمان', 'بازیابی ۴۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'divine', 2500, 12500, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون HP قهرمان')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون HP سطح ۸۰+ 10000', 'از سطح ۸۰ به بالا؛ بازیابی ۱۰٬۰۰۰ HP، تا سقف HP حداکثر قهرمان.', 'potion', 'divine', 5000, 25000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون HP سطح ۸۰+ 10000')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔷 معجون Mana کوچک', 'بازیابی ۲۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'common', 25, 120, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔷 معجون Mana کوچک')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔷 معجون Mana متوسط', 'بازیابی ۲۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'uncommon', 50, 250, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔷 معجون Mana متوسط')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔷 معجون Mana بزرگ', 'بازیابی ۴۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'rare', 100, 500, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔷 معجون Mana بزرگ')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔷 معجون Mana ممتاز', 'بازیابی ۴۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'epic', 200, 1000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔷 معجون Mana ممتاز')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔷 معجون Mana افسانه‌ای', 'بازیابی ۴۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'legendary', 400, 2000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔷 معجون Mana افسانه‌ای')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔷 معجون Mana اسطوره‌ای', 'بازیابی ۴۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'mythic', 800, 4000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔷 معجون Mana اسطوره‌ای')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔷 معجون Mana کهن', 'بازیابی ۴۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'divine', 1200, 6000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔷 معجون Mana کهن')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔷 معجون Mana ابدی', 'بازیابی ۴۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'divine', 1800, 9000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔷 معجون Mana ابدی')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔷 معجون Mana قهرمان', 'بازیابی ۴۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.', 'potion', 'divine', 2500, 12500, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔷 معجون Mana قهرمان')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔷 معجون Mana سطح ۸۰+ 10000', 'از سطح ۸۰ به بالا؛ بازیابی ۱۰٬۰۰۰ Mana، تا سقف Mana حداکثر قهرمان.', 'potion', 'divine', 5000, 25000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔷 معجون Mana سطح ۸۰+ 10000')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🌿 گیاه اِلدوریا', 'مادهٔ لازم برای ساخت و ارتقای تجهیزات.', 'material', 'common', 20, 80, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🌿 گیاه اِلدوریا')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '⛏️ تکه‌آهن گابلین', 'مادهٔ لازم برای ارتقای تجهیزات سطح متوسط.', 'material', 'uncommon', 50, 200, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '⛏️ تکه‌آهن گابلین')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '💎 خرده‌سنگ جادویی', 'مادهٔ لازم برای ارتقای تجهیزات جادویی.', 'material', 'rare', 100, 450, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '💎 خرده‌سنگ جادویی')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🔥 فلس اژدها', 'مادهٔ کمیاب برای ارتقای تجهیزات سطح بالا.', 'material', 'epic', 250, 1000, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🔥 فلس اژدها')"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🦴 پنجهٔ گرگ', 'مادهٔ ساخت تجهیزات سبک.', 'material', 'common', 30, 120, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🦴 پنجهٔ گرگ')"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۲۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.' WHERE name IN ('🧪 معجون سلامتی', '🧪 معجون HP کوچک')"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۴۰٪ از حداکثر HP؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.' WHERE name IN ('🧪 معجون سلامتی بزرگ', '🧪 معجون HP بزرگ')"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۲۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.' WHERE name IN ('🔷 معجون مانا', '🧪 معجون مانا')"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۴۰٪ از حداکثر Mana؛ مقدار واقعی به ظرفیت باقی‌مانده محدود می‌شود.' WHERE name IN ('🧪 معجون مانای بزرگ', '🔷 معجون مانای بزرگ')"))
    op.execute(sa.text("UPDATE items SET buy_price = CASE name WHEN '🌿 گیاه اِلدوریا' THEN 80 WHEN '⛏️ تکه‌آهن گابلین' THEN 200 WHEN '💎 خرده‌سنگ جادویی' THEN 450 WHEN '🔥 فلس اژدها' THEN 1000 WHEN '🦴 پنجهٔ گرگ' THEN 120 ELSE buy_price END WHERE name IN ('🌿 گیاه اِلدوریا','⛏️ تکه‌آهن گابلین','💎 خرده‌سنگ جادویی','🔥 فلس اژدها','🦴 پنجهٔ گرگ')"))
    op.execute(sa.text("UPDATE items SET buy_price = 0 WHERE item_type = 'potion' AND name NOT IN ('🧪 معجون سلامتی', '🧪 معجون سلامتی بزرگ', '🔷 معجون مانا', '🧪 معجون مانای بزرگ')"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۲۰٪ از حداکثر HP؛ بیش از ظرفیت باقی‌مانده بازیابی نمی‌شود.', buy_price = 100 WHERE name = '🧪 معجون سلامتی'"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۴۰٪ از حداکثر HP؛ بیش از ظرفیت باقی‌مانده بازیابی نمی‌شود.', buy_price = 250 WHERE name = '🧪 معجون سلامتی بزرگ'"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۲۰٪ از حداکثر Mana؛ بیش از ظرفیت باقی‌مانده بازیابی نمی‌شود.', buy_price = 300 WHERE name = '🔷 معجون مانا'"))
    op.execute(sa.text("INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at) SELECT '🧪 معجون مانای بزرگ', 'بازیابی ۴۰٪ از حداکثر Mana؛ بیش از ظرفیت باقی‌مانده بازیابی نمی‌شود.', 'potion', 'rare', 200, 800, TRUE, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون مانای بزرگ')"))
    op.execute(sa.text("UPDATE items SET description = 'بازیابی ۴۰٪ از حداکثر Mana؛ بیش از ظرفیت باقی‌مانده بازیابی نمی‌شود.', buy_price = 800 WHERE name = '🧪 معجون مانای بزرگ'"))
    op.add_column("characters", sa.Column("dead_until", sa.DateTime(), nullable=True))
    op.add_column("character_pets", sa.Column("training_completed_at", sa.DateTime(), nullable=True))
    op.add_column("character_pets", sa.Column("training_notified_at", sa.DateTime(), nullable=True))
    op.add_column("character_pets", sa.Column("training_start_level", sa.Integer(), nullable=True))
    # Legacy training granted XP immediately; mark those records completed to avoid duplicate XP.
    op.execute(sa.text("UPDATE character_pets SET training_completed_at = last_training_at, training_notified_at = last_training_at, training_start_level = level WHERE last_training_at IS NOT NULL"))
    op.create_table(
        "group_fan_art_spawns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("fan_art_id", sa.Integer(), sa.ForeignKey("fan_arts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("spawned_at", sa.DateTime(), nullable=False),
        sa.Column("claimed_by", sa.BigInteger(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("chat_id", name="uq_group_fan_art_spawn_chat"),
    )
    op.create_index("ix_group_fan_art_spawns_chat_id", "group_fan_art_spawns", ["chat_id"])
    op.create_index("ix_group_fan_art_spawns_fan_art_id", "group_fan_art_spawns", ["fan_art_id"])
    op.create_index("ix_group_fan_art_spawns_spawned_at", "group_fan_art_spawns", ["spawned_at"])
    op.create_index("ix_group_fan_art_spawns_claimed_by", "group_fan_art_spawns", ["claimed_by"])
    op.create_table(
        "group_boss_attack_cooldowns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("boss_id", sa.Integer(), sa.ForeignKey("group_bosses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("last_attack_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("boss_id", "telegram_id", name="uq_group_boss_player_cooldown"),
    )
    op.create_index("ix_group_boss_attack_cooldowns_boss_id", "group_boss_attack_cooldowns", ["boss_id"])
    op.create_index("ix_group_boss_attack_cooldowns_telegram_id", "group_boss_attack_cooldowns", ["telegram_id"])

def downgrade():
    op.drop_constraint("uq_fan_art_owner_art", "fan_art_ownerships", type_="unique")
    op.drop_column("fan_arts", "value_gold")
    op.drop_table("group_boss_attack_cooldowns")
    op.drop_table("group_fan_art_spawns")
    op.drop_column("characters", "dead_until")
    op.drop_column("character_pets", "training_start_level")
    op.drop_column("character_pets", "training_notified_at")
    op.drop_column("character_pets", "training_completed_at")
