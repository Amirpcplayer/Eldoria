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