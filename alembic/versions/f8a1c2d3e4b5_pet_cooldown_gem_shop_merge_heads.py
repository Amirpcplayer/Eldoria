"""Add pet training cooldown and gem-priced equipment; merge existing heads."""
from alembic import op
import sqlalchemy as sa

revision = "f8a1c2d3e4b5"
down_revision = ("e2f3a4b5c6d7", "add_telegram_username", "2d3e4f5a6b7c")
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("character_pets", sa.Column("last_training_at", sa.DateTime(), nullable=True))
    op.add_column("equipments", sa.Column("gem_price", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_equipments_gem_price", "equipments", ["gem_price"], unique=False)

    now = sa.text("CURRENT_TIMESTAMP")
    equipment_table = sa.table(
        "equipments",
        sa.column("name", sa.String), sa.column("description", sa.Text),
        sa.column("set_key", sa.String), sa.column("equipment_type", sa.String),
        sa.column("rarity", sa.String), sa.column("required_level", sa.Integer),
        sa.column("shop_price", sa.Integer), sa.column("gem_price", sa.Integer),
        sa.column("attack", sa.Integer), sa.column("magic_power", sa.Integer),
        sa.column("defense", sa.Integer), sa.column("magic_defense", sa.Integer),
        sa.column("hp", sa.Integer), sa.column("mana", sa.Integer),
        sa.column("speed", sa.Integer), sa.column("accuracy", sa.Integer),
        sa.column("critical", sa.Integer), sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    swords = [
        ("شمشیر آهنی", "شمشیری ساده و قابل اعتماد.", "common", 1, 250, 0, 5),
        ("شمشیر فولادی", "تیغه‌ای مقاوم برای ماجراجویان باتجربه.", "uncommon", 5, 1200, 0, 10),
        ("شمشیر شکارچی", "سبک و مناسب نبردهای سریع.", "uncommon", 8, 1900, 0, 13),
        ("شمشیر نقره‌ای", "تیغه‌ای درخشان با نیروی پاک.", "rare", 12, 4200, 0, 18),
        ("شمشیر باد", "تیغه‌ای سبک که با جریان باد حرکت می‌کند.", "rare", 18, 8000, 0, 25),
        ("شمشیر یخی", "لبه‌ای سرد و برنده.", "rare", 22, 11000, 0, 30),
        ("شمشیر آذرخش", "در هر ضربه انرژی الکتریکی دارد.", "epic", 28, 18000, 0, 40),
        ("شمشیر شعله", "شمشیری آغشته به جادوی آتش.", "epic", 32, 24000, 0, 48),
        ("تیغهٔ سایه", "سلاحی کمیاب با نیروی تاریکی.", "epic", 40, 36000, 0, 60),
        ("شمشیر اژدها", "از فولاد و قدرت اژدها ساخته شده.", "legendary", 50, 0, 35, 78),
        ("تیغهٔ ققنوس", "تیغه‌ای افسانه‌ای با نیروی شعلهٔ جاودان.", "mythic", 65, 0, 60, 105),
        ("شمشیر آسمانی اِلدوریا", "سلاحی اسطوره‌ای برای قهرمانان برگزیده.", "divine", 80, 0, 100, 145),
    ]
    rows = []
    for name, description, rarity, level, gold, gems, attack in swords:
        rows.append(dict(name=name, description=description, set_key=None,
            equipment_type="weapon", rarity=rarity, required_level=level,
            shop_price=gold, gem_price=gems, attack=attack, magic_power=0,
            defense=0, magic_defense=0, hp=0, mana=0, speed=0, accuracy=0,
            critical=0, is_active=True, created_at=None))
    # Use database timestamp default explicitly rather than NULL for NOT NULL column.
    for row in rows:
        row["created_at"] = __import__("datetime").datetime.utcnow()
    op.bulk_insert(equipment_table, rows)

    item_table = sa.table(
        "items", sa.column("name", sa.String), sa.column("description", sa.Text),
        sa.column("item_type", sa.String), sa.column("rarity", sa.String),
        sa.column("sell_price", sa.Integer), sa.column("buy_price", sa.Integer),
        sa.column("is_tradeable", sa.Boolean), sa.column("created_at", sa.DateTime),
    )
    materials = [
        ("🪵 چوب", "چوب مناسب ساخت سلاح و ابزار.", "material", "common", 2, 12),
        ("⛓️ سنگ آهن", "سنگ آهن خام برای آهنگری.", "material", "common", 3, 18),
        ("🔩 شمش آهن", "فلز پالایش‌شده برای ساخت تجهیزات.", "material", "uncommon", 8, 45),
        ("🍃 برگ اِلدوریا", "گیاهی جادویی برای ساخت معجون.", "material", "common", 2, 15),
        ("🌿 گیاه درمانی", "مادهٔ اولیهٔ ساخت معجون‌های درمانی.", "material", "common", 3, 20),
        ("💎 خرده‌سنگ جادویی", "ماده‌ای کمیاب برای ارتقای تجهیزات.", "material", "rare", 20, 120),
        ("🔥 فلس اژدها", "فلسی کمیاب برای ساخت تجهیزات سطح بالا.", "material", "epic", 50, 350),
    ]
    item_rows = [dict(name=n, description=d, item_type=t, rarity=r, sell_price=sp,
                      buy_price=bp, is_tradeable=True,
                      created_at=__import__("datetime").datetime.utcnow())
                 for n,d,t,r,sp,bp in materials]
    op.bulk_insert(item_table, item_rows)

    quest_table = sa.table(
        "quests",
        sa.column("name", sa.String), sa.column("description", sa.Text),
        sa.column("category", sa.String), sa.column("objective_type", sa.String),
        sa.column("target_id", sa.Integer), sa.column("required_amount", sa.Integer),
        sa.column("min_level", sa.Integer), sa.column("prerequisite_quest_id", sa.Integer),
        sa.column("reward_xp", sa.Integer), sa.column("reward_skill_xp", sa.Integer),
        sa.column("reward_gold", sa.Integer), sa.column("reward_equipment_id", sa.Integer),
        sa.column("is_repeatable", sa.Boolean), sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    new_quests = [
        ("🐺 پاک‌سازی جنگل", "ده دشمن را در ماجراجویی شکست بده.", "story", "kill_enemy", None, 10, 3, None, 900, 120, 500, None, False, True, __import__("datetime").datetime.utcnow()),
        ("🛡 آمادهٔ نبرد", "یک قطعه تجهیزات بپوش.", "story", "equip", None, 1, 1, None, 250, 50, 150, None, False, True, __import__("datetime").datetime.utcnow()),
        ("⚔️ استاد شکار", "پنجاه دشمن را شکست بده.", "achievement", "kill_enemy", None, 50, 5, None, 3000, 500, 1500, None, False, True, __import__("datetime").datetime.utcnow()),
        ("📈 قهرمان سطح ده", "به سطح ۱۰ برس.", "story", "level", 10, 10, 1, None, 1200, 200, 600, None, False, True, __import__("datetime").datetime.utcnow()),
        ("🔮 شاگرد جادو", "یک مهارت یاد بگیر.", "story", "learn_skill", None, 1, 1, None, 600, 150, 300, None, False, True, __import__("datetime").datetime.utcnow()),
        ("🏹 شکارچی گابلین نخبه", "پنج گابلین را شکست بده.", "achievement", "kill_enemy", None, 5, 5, None, 1300, 180, 700, None, False, True, __import__("datetime").datetime.utcnow()),
        ("🌟 مسیر افسانه", "به سطح ۵۰ برس.", "achievement", "level", 50, 50, 20, None, 12000, 2500, 10000, None, False, True, __import__("datetime").datetime.utcnow()),
    ]
    op.execute("UPDATE quests SET category='story', name='⚔️ شکارچی پیوسته' WHERE name='⚔️ شکار روزانه'")
    op.bulk_insert(quest_table, [
        dict(zip(
            ["name","description","category","objective_type","target_id","required_amount","min_level","prerequisite_quest_id","reward_xp","reward_skill_xp","reward_gold","reward_equipment_id","is_repeatable","is_active","created_at"],
            row,
        ))
        for row in new_quests
    ])

def downgrade():
    op.drop_index("ix_equipments_gem_price", table_name="equipments")
    op.drop_column("equipments", "gem_price")
    op.drop_column("character_pets", "last_training_at")
