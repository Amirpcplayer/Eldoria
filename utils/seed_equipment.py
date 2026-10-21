import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.equipment import Equipment


EQUIPMENT_DATA = [
    {
        "name": "⚔️ شمشیر آهنی",
        "description": "یک شمشیر ساده و قابل اعتماد برای شروع ماجراجویی.",
        "equipment_type": "weapon",
        "rarity": "common",
        "required_level": 1,
        "shop_price": 500,
        "attack": 15,
        "magic_power": 0,
        "defense": 0,
        "magic_defense": 0,
        "hp": 0,
        "mana": 0,
        "speed": 0,
        "accuracy": 0,
        "critical": 0,
    },
    {
        "name": "🔥 شمشیر شعله‌ای",
        "description": "شمشیری آغشته به نیروی آتش که قدرت فیزیکی و جادویی را افزایش می‌دهد.",
        "equipment_type": "weapon",
        "rarity": "uncommon",
        "required_level": 10,
        "shop_price": 1500,
        "attack": 30,
        "magic_power": 10,
        "defense": 0,
        "magic_defense": 0,
        "hp": 0,
        "mana": 0,
        "speed": 0,
        "accuracy": 0,
        "critical": 0,
    },
    {
        "name": "🪖 کلاه آهنی",
        "description": "کلاه‌خودی ساده اما مقاوم که از سر قهرمان محافظت می‌کند.",
        "equipment_type": "helmet",
        "rarity": "common",
        "required_level": 1,
        "shop_price": 600,
        "attack": 0,
        "magic_power": 0,
        "defense": 20,
        "magic_defense": 5,
        "hp": 0,
        "mana": 0,
        "speed": 0,
        "accuracy": 0,
        "critical": 0,
    },
    {
        "name": "🛡️ زره آهنی",
        "description": "زره‌ای سنگین و مقاوم که دفاع و سلامت قهرمان را افزایش می‌دهد.",
        "equipment_type": "armor",
        "rarity": "common",
        "required_level": 1,
        "shop_price": 1200,
        "attack": 0,
        "magic_power": 0,
        "defense": 35,
        "magic_defense": 10,
        "hp": 100,
        "mana": 0,
        "speed": 0,
        "accuracy": 0,
        "critical": 0,
    },
    {
        "name": "👢 چکمه مسافرتی",
        "description": "چکمه‌هایی سبک و مناسب برای سفرهای طولانی و مبارزه.",
        "equipment_type": "boots",
        "rarity": "common",
        "required_level": 1,
        "shop_price": 800,
        "attack": 0,
        "magic_power": 0,
        "defense": 5,
        "magic_defense": 0,
        "hp": 0,
        "mana": 0,
        "speed": 10,
        "accuracy": 0,
        "critical": 0,
    },
    {
        "name": "💍 انگشتر قدرت",
        "description": "انگشتری جادویی که نیروی حمله و شانس ضربه حیاتی را افزایش می‌دهد.",
        "equipment_type": "ring",
        "rarity": "uncommon",
        "required_level": 10,
        "shop_price": 1000,
        "attack": 20,
        "magic_power": 0,
        "defense": 0,
        "magic_defense": 0,
        "hp": 0,
        "mana": 0,
        "speed": 0,
        "accuracy": 0,
        "critical": 5,
    },
    {
        "name": "📿 گردنبند جادو",
        "description": "گردنبندی اسرارآمیز که قدرت جادویی و ذخیره مانا را افزایش می‌دهد.",
        "equipment_type": "necklace",
        "rarity": "uncommon",
        "required_level": 10,
        "shop_price": 1200,
        "attack": 0,
        "magic_power": 25,
        "defense": 0,
        "magic_defense": 5,
        "hp": 0,
        "mana": 100,
        "speed": 0,
        "accuracy": 0,
        "critical": 0,
    },
]


# ست‌های کامل؛ هر ست شامل شش اسلات استاندارد است.
SET_ITEMS = [
    # نگهبان اِلدوریا: دفاعی
    ("🪖 کلاه نگهبان اِلدوریا", "helmet", "eldoria_guardian", 5, 900, 0, 0, 12, 5, 40, 0, 0, 0, 0),
    ("🛡️ زره نگهبان اِلدوریا", "armor", "eldoria_guardian", 8, 1800, 0, 0, 24, 12, 120, 0, 0, 0, 0),
    ("👢 چکمه نگهبان اِلدوریا", "boots", "eldoria_guardian", 6, 1100, 0, 0, 8, 4, 35, 0, 5, 0, 0),
    ("⚔️ شمشیر نگهبان اِلدوریا", "weapon", "eldoria_guardian", 7, 1500, 18, 0, 5, 0, 30, 0, 0, 0, 0),
    ("💍 انگشتر نگهبان اِلدوریا", "ring", "eldoria_guardian", 8, 1300, 4, 0, 6, 3, 25, 0, 0, 0, 0),
    ("📿 گردنبند نگهبان اِلدوریا", "necklace", "eldoria_guardian", 8, 1400, 0, 0, 8, 8, 50, 0, 0, 0, 0),
    # طوفان آرکین: جادویی
    ("🪖 تاج طوفان آرکین", "helmet", "arcane_storm", 15, 4200, 0, 18, 3, 12, 0, 35, 0, 4, 2),
    ("🛡️ ردای طوفان آرکین", "armor", "arcane_storm", 18, 6500, 0, 25, 8, 20, 40, 70, 0, 0, 2),
    ("👢 چکمه طوفان آرکین", "boots", "arcane_storm", 16, 4800, 0, 12, 3, 8, 0, 35, 12, 5, 2),
    ("⚔️ عصای طوفان آرکین", "weapon", "arcane_storm", 15, 5000, 5, 45, 0, 5, 0, 80, 0, 0, 5),
    ("💍 انگشتر طوفان آرکین", "ring", "arcane_storm", 17, 5200, 2, 22, 0, 8, 0, 45, 0, 3, 4),
    ("📿 گردنبند طوفان آرکین", "necklace", "arcane_storm", 18, 5800, 0, 30, 2, 12, 0, 100, 0, 0, 4),
    # امپراتور اژدها: تهاجمی
    ("🪖 تاج امپراتور اژدها", "helmet", "dragon_emperor", 35, 18000, 8, 5, 18, 12, 100, 30, 0, 4, 5),
    ("🛡️ زره امپراتور اژدها", "armor", "dragon_emperor", 38, 25000, 5, 8, 35, 25, 220, 30, 0, 0, 5),
    ("👢 چکمه امپراتور اژدها", "boots", "dragon_emperor", 36, 19500, 8, 3, 12, 8, 90, 20, 12, 4, 4),
    ("⚔️ تیغه امپراتور اژدها", "weapon", "dragon_emperor", 35, 22000, 55, 15, 5, 5, 80, 25, 0, 2, 12),
    ("💍 انگشتر امپراتور اژدها", "ring", "dragon_emperor", 37, 20500, 18, 10, 8, 8, 80, 20, 0, 4, 8),
    ("📿 گردنبند امپراتور اژدها", "necklace", "dragon_emperor", 38, 21500, 12, 20, 8, 15, 120, 55, 0, 0, 8),
    # سایه ماه: سرعت و دقت
    ("🪖 نقاب سایه ماه", "helmet", "moonshadow", 25, 9500, 10, 5, 8, 8, 30, 15, 12, 12, 8),
    ("🛡️ زره سایه ماه", "armor", "moonshadow", 28, 13000, 8, 8, 18, 15, 100, 25, 8, 10, 8),
    ("👢 چکمه سایه ماه", "boots", "moonshadow", 26, 10500, 8, 5, 8, 8, 40, 15, 20, 15, 8),
    ("⚔️ خنجر سایه ماه", "weapon", "moonshadow", 25, 11500, 38, 8, 0, 0, 20, 10, 15, 12, 14),
    ("💍 انگشتر سایه ماه", "ring", "moonshadow", 27, 10000, 12, 5, 4, 4, 20, 10, 10, 10, 12),
    ("📿 گردنبند سایه ماه", "necklace", "moonshadow", 28, 10800, 8, 12, 4, 8, 50, 25, 12, 12, 10),
]

for name, equipment_type, set_key, required_level, shop_price, attack, magic_power, defense, magic_defense, hp, mana, speed, accuracy, critical in SET_ITEMS:
    EQUIPMENT_DATA.append({
        "name": name,
        "description": f"قطعه‌ای از ست {'نگهبان اِلدوریا' if set_key == 'eldoria_guardian' else 'طوفان آرکین' if set_key == 'arcane_storm' else 'امپراتور اژدها' if set_key == 'dragon_emperor' else 'سایه ماه'}؛ با پوشیدن چند قطعه، پاداش ست فعال می‌شود.",
        "equipment_type": equipment_type,
        "rarity": "rare" if required_level < 20 else "epic" if required_level < 35 else "legendary",
        "required_level": required_level,
        "shop_price": shop_price,
        "set_key": set_key,
        "attack": attack,
        "magic_power": magic_power,
        "defense": defense,
        "magic_defense": magic_defense,
        "hp": hp,
        "mana": mana,
        "speed": speed,
        "accuracy": accuracy,
        "critical": critical,
    })


# تجهیزات اندگیم؛ این آیتم‌ها به‌صورت افزایشی seed می‌شوند و آیتم‌های قدیمی حذف نمی‌شوند.
# هر رده ۶ اسلات کامل دارد و قدرت آن از rarity multiplier مرکزی تبعیت می‌کند.
_ENDGAME_SLOTS = [
    ("helmet", "کلاه‌خود"),
    ("armor", "زره"),
    ("boots", "چکمه"),
    ("weapon", "سلاح"),
    ("ring", "انگشتر"),
    ("necklace", "گردنبند"),
]
_ENDGAME_TIERS = [
    (50, "epic", 220_000, "نیمه‌جهانی"),
    (75, "legendary", 1_800_000, "اسطوره‌ای"),
    (100, "mythic", 12_000_000, "اِلدوریایی"),
]
_ENDGAME_SETS = [
    {
        "set_key": "dragon_overlord_endgame",
        "prefix": "اژدهای فرمانروا",
        "attack": [20, 20, 20, 120, 20, 20],
        "magic_power": [5, 5, 5, 25, 5, 15],
        "defense": [8, 20, 8, 5, 8, 8],
        "magic_defense": [5, 12, 5, 3, 5, 8],
        "hp": [30, 120, 35, 25, 25, 40],
        "mana": [10, 20, 10, 15, 15, 30],
        "speed": [5, 0, 15, 0, 5, 5],
        "accuracy": [5, 0, 8, 2, 5, 0],
        "critical": [5, 3, 5, 15, 10, 10],
    },
    {
        "set_key": "void_archmage",
        "prefix": "جادوگر خلأ",
        "attack": [5, 5, 5, 20, 5, 5],
        "magic_power": [20, 25, 15, 120, 20, 30],
        "defense": [5, 12, 5, 0, 3, 3],
        "magic_defense": [12, 25, 10, 8, 12, 18],
        "hp": [20, 80, 20, 0, 15, 20],
        "mana": [50, 100, 50, 120, 80, 150],
        "speed": [5, 0, 15, 0, 5, 5],
        "accuracy": [5, 0, 8, 2, 5, 0],
        "critical": [3, 3, 5, 8, 5, 5],
    },
    {
        "set_key": "astral_vanguard",
        "prefix": "پیشتاز اختر",
        "attack": [10, 5, 5, 30, 5, 5],
        "magic_power": [5, 5, 5, 10, 5, 5],
        "defense": [25, 35, 20, 15, 15, 15],
        "magic_defense": [15, 25, 12, 8, 10, 15],
        "hp": [100, 250, 80, 50, 50, 80],
        "mana": [10, 20, 10, 10, 15, 25],
        "speed": [3, 0, 8, 0, 3, 3],
        "accuracy": [3, 0, 5, 0, 3, 0],
        "critical": [2, 2, 3, 5, 4, 4],
    },
]

for level, rarity, price, tier_label in _ENDGAME_TIERS:
    for set_data in _ENDGAME_SETS:
        for index, (slot, slot_name) in enumerate(_ENDGAME_SLOTS):
            name = f"✨ {slot_name} {set_data['prefix']} {tier_label}"
            item = {
                "name": name,
                "description": f"تجهیز اندگیم سطح {level}؛ بخشی از ست {set_data['prefix']}.",
                "set_key": set_data["set_key"],
                "equipment_type": slot,
                "rarity": rarity,
                "required_level": level,
                "shop_price": price,
                "gem_price": 0,
            }
            for stat in ("attack", "magic_power", "defense", "magic_defense", "hp", "mana", "speed", "accuracy", "critical"):
                item[stat] = set_data[stat][index]
            EQUIPMENT_DATA.append(item)


async def seed_equipment() -> None:
    added = 0
    updated = 0

    async with AsyncSessionLocal() as session:
        for data in EQUIPMENT_DATA:
            result = await session.execute(
                select(Equipment).where(
                    Equipment.name == data["name"]
                )
            )

            equipment = result.scalar_one_or_none()

            if equipment is None:
                equipment = Equipment(**data)
                session.add(equipment)
                added += 1
                continue

            changed = False

            for key, value in data.items():
                if getattr(equipment, key) != value:
                    setattr(equipment, key, value)
                    changed = True

            if changed:
                updated += 1

        await session.commit()

    print(
        "✅ Equipment seeded successfully. "
        f"Added: {added}, Updated: {updated}"
    )


if __name__ == "__main__":
    asyncio.run(seed_equipment())
