from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.skill import Skill


skills = [
    {
        "name": "🔥 جادوی آتش",
        "description": "قدرت جادوی آتش برای حمله به دشمن.",
        "element": "fire",
        "skill_type": "magic",
        "target_type": "single",
        "rarity": "common",
        "max_level": 10,
        "base_power": 50,
        "power_per_level": 110,
        "mana_cost": 50,
        "cooldown": 5,
        "unlock_level": 0,
    },
    {
        "name": "💧 جادوی آب",
        "description": "قدرت جادوی آب برای حمله به دشمن.",
        "element": "water",
        "skill_type": "magic",
        "target_type": "single",
        "rarity": "common",
        "max_level": 10,
        "base_power": 55,
        "power_per_level": 115,
        "mana_cost": 50,
        "cooldown": 5,
        "unlock_level": 0,
    },
    {
        "name": "🌪️ جادوی باد",
        "description": "قدرت جادوی باد برای حمله به دشمن.",
        "element": "wind",
        "skill_type": "magic",
        "target_type": "single",
        "rarity": "common",
        "max_level": 10,
        "base_power": 60,
        "power_per_level": 120,
        "mana_cost": 55,
        "cooldown": 5,
        "unlock_level": 0,
    },
    {
        "name": "🪨 جادوی خاک",
        "description": "قدرت جادوی خاک برای حمله به دشمن.",
        "element": "earth",
        "skill_type": "magic",
        "target_type": "single",
        "rarity": "common",
        "max_level": 10,
        "base_power": 70,
        "power_per_level": 125,
        "mana_cost": 60,
        "cooldown": 7,
        "unlock_level": 0,
    },
    {
        "name": "⚡ جادوی الکترو",
        "description": "جادوی قدرتمند الکترو برای حمله به دشمن.",
        "element": "electro",
        "skill_type": "magic",
        "target_type": "single",
        "rarity": "rare",
        "max_level": 10,
        "base_power": 80,
        "power_per_level": 140,
        "mana_cost": 75,
        "cooldown": 8,
        "unlock_level": 20,
    },
    {
        "name": "❄️ جادوی یخ",
        "description": "جادوی یخ برای حمله به دشمن.",
        "element": "ice",
        "skill_type": "magic",
        "target_type": "single",
        "rarity": "rare",
        "max_level": 10,
        "base_power": 85,
        "power_per_level": 145,
        "mana_cost": 80,
        "cooldown": 10,
        "unlock_level": 20,
    },
    {
        "name": "☀️ جادوی افسانه‌ای نور",
        "description": "جادوی افسانه‌ای نور برای حمله‌ای بسیار قدرتمند.",
        "element": "light",
        "skill_type": "magic",
        "target_type": "single",
        "rarity": "legendary",
        "max_level": 10,
        "base_power": 100,
        "power_per_level": 170,
        "mana_cost": 110,
        "cooldown": 12,
        "unlock_level": 60,
    },
    {
        "name": "🌑 جادوی افسانه‌ای تاریکی",
        "description": "جادوی افسانه‌ای تاریکی برای حمله‌ای بسیار قدرتمند.",
        "element": "dark",
        "skill_type": "magic",
        "target_type": "single",
        "rarity": "legendary",
        "max_level": 10,
        "base_power": 110,
        "power_per_level": 180,
        "mana_cost": 120,
        "cooldown": 12,
        "unlock_level": 60,
    },
]


async def seed_skills():
    async with AsyncSessionLocal() as session:

        added = 0

        for skill_data in skills:

            result = await session.execute(
                select(Skill).where(
                    Skill.element == skill_data["element"]
                )
            )

            existing_skill = result.scalar_one_or_none()

            if existing_skill is not None:

                existing_skill.name = skill_data["name"]
                existing_skill.description = skill_data["description"]
                existing_skill.skill_type = skill_data["skill_type"]
                existing_skill.target_type = skill_data["target_type"]
                existing_skill.rarity = skill_data["rarity"]
                existing_skill.max_level = skill_data["max_level"]
                existing_skill.base_power = skill_data["base_power"]
                existing_skill.power_per_level = skill_data["power_per_level"]
                existing_skill.mana_cost = skill_data["mana_cost"]
                existing_skill.cooldown = skill_data["cooldown"]
                existing_skill.unlock_level = skill_data["unlock_level"]
                existing_skill.is_active = True

            else:

                session.add(
                    Skill(**skill_data)
                )

                added += 1

        await session.commit()

        print(
            f"✅ Skills seeded successfully. Added: {added}"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_skills())