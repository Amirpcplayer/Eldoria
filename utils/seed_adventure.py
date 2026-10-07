import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.adventure import (
    AdventureArea,
    AdventureEnemy,
)


# ============================================================
# REWARD CALCULATOR
# ============================================================

def calculate_enemy_rewards(
    level: int,
) -> tuple[int, int, int]:
    """
    محاسبه خودکار پاداش دشمن بر اساس Level.

    XP:
        100 + (Level × 75)

    Skill XP:
        25 + (Level × 15)

    Gold:
        20 + (Level × 25)
    """

    level = max(1, level)

    xp_reward = 100 + (level * 75)

    skill_xp_reward = 25 + (level * 15)

    gold_reward = 20 + (level * 25)

    return (
        xp_reward,
        skill_xp_reward,
        gold_reward,
    )


# ============================================================
# AREAS
# ============================================================

AREAS = [
    {
        "name": "🌲 جنگل اِلدوریا",
        "description": (
            "جنگلی سرسبز و مرموز که اولین ماجراجویان "
            "اِلدوریا سفر خود را از آن آغاز می‌کنند."
        ),
        "recommended_level": 1,
        "min_level": 1,
        "max_level": 10,
    },
    {
        "name": "⛰️ کوهستان سنگی",
        "description": (
            "کوهستانی خطرناک با موجودات قدرتمند و "
            "صخره‌های عظیم."
        ),
        "recommended_level": 10,
        "min_level": 10,
        "max_level": 20,
    },
    {
        "name": "🏜️ بیابان سرخ",
        "description": (
            "بیابانی وسیع که موجودات مرگبار در آن "
            "در کمین مسافران هستند."
        ),
        "recommended_level": 20,
        "min_level": 20,
        "max_level": 35,
    },
    {
        "name": "🌋 سرزمین آتشفشانی",
        "description": (
            "سرزمینی پوشیده از گدازه و موجودات "
            "آتشی بسیار قدرتمند."
        ),
        "recommended_level": 35,
        "min_level": 35,
        "max_level": 50,
    },
    {
        "name": "🌑 سرزمین سایه‌ها",
        "description": (
            "قلمروی تاریک که موجودات سایه‌ای "
            "در آن زندگی می‌کنند."
        ),
        "recommended_level": 50,
        "min_level": 50,
        "max_level": 70,
    },
    {
        "name": "🏰 قلمرو افسانه‌ای",
        "description": (
            "آخرین سرزمین شناخته‌شده؛ جایی که "
            "موجودات افسانه‌ای زندگی می‌کنند."
        ),
        "recommended_level": 70,
        "min_level": 70,
        "max_level": 100,
    },
]


# ============================================================
# ENEMIES
# ============================================================

ENEMIES = [
    {
        "name": "🐺 گرگ وحشی",
        "description": "گرگی سریع و خطرناک.",
        "level": 1,
        "hp": 100,
        "attack": 12,
        "defense": 5,
        "area": "🌲 جنگل اِلدوریا",
    },
    {
        "name": "👺 گابلین",
        "description": "موجودی کوچک اما مهاجم.",
        "level": 3,
        "hp": 150,
        "attack": 18,
        "defense": 8,
        "area": "🌲 جنگل اِلدوریا",
    },
    {
        "name": "🗡️ راهزن جنگل",
        "description": "راهزنی که در مسیرهای جنگل کمین می‌کند.",
        "level": 7,
        "hp": 250,
        "attack": 28,
        "defense": 15,
        "area": "🌲 جنگل اِلدوریا",
    },
    {
        "name": "🪨 گولم سنگی",
        "description": "موجودی ساخته‌شده از سنگ.",
        "level": 12,
        "hp": 700,
        "attack": 55,
        "defense": 45,
        "area": "⛰️ کوهستان سنگی",
    },
    {
        "name": "🐻 خرس کوهستانی",
        "description": "خرسی عظیم و بسیار قدرتمند.",
        "level": 16,
        "hp": 900,
        "attack": 70,
        "defense": 35,
        "area": "⛰️ کوهستان سنگی",
    },
    {
        "name": "🦂 عقرب غول‌پیکر",
        "description": "عقربی سمی که در شن‌ها پنهان می‌شود.",
        "level": 23,
        "hp": 1200,
        "attack": 95,
        "defense": 55,
        "area": "🏜️ بیابان سرخ",
    },
    {
        "name": "🐍 مار شنی",
        "description": "ماری عظیم که در زیر شن‌ها حرکت می‌کند.",
        "level": 30,
        "hp": 1800,
        "attack": 125,
        "defense": 70,
        "area": "🏜️ بیابان سرخ",
    },
    {
        "name": "🔥 گولم آتشین",
        "description": "گولمی ساخته‌شده از سنگ و آتش.",
        "level": 38,
        "hp": 3000,
        "attack": 180,
        "defense": 110,
        "area": "🌋 سرزمین آتشفشانی",
    },
    {
        "name": "🐉 دریک آتشین",
        "description": "اژدهایی کوچک اما بسیار خطرناک.",
        "level": 47,
        "hp": 4500,
        "attack": 240,
        "defense": 140,
        "area": "🌋 سرزمین آتشفشانی",
    },
    {
        "name": "👻 روح تاریک",
        "description": "روحی قدرتمند از اعماق تاریکی.",
        "level": 55,
        "hp": 6000,
        "attack": 300,
        "defense": 170,
        "area": "🌑 سرزمین سایه‌ها",
    },
    {
        "name": "😈 شیطان سایه",
        "description": "موجودی اهریمنی که از سایه‌ها تغذیه می‌کند.",
        "level": 65,
        "hp": 8500,
        "attack": 400,
        "defense": 220,
        "area": "🌑 سرزمین سایه‌ها",
    },
    {
        "name": "🦄 موجود افسانه‌ای",
        "description": "موجودی کمیاب با قدرتی ناشناخته.",
        "level": 75,
        "hp": 12000,
        "attack": 550,
        "defense": 300,
        "area": "🏰 قلمرو افسانه‌ای",
    },
    {
        "name": "🐲 اژدهای باستانی",
        "description": "یکی از قدرتمندترین موجودات اِلدوریا.",
        "level": 90,
        "hp": 25000,
        "attack": 900,
        "defense": 500,
        "area": "🏰 قلمرو افسانه‌ای",
    },
]


# ============================================================
# SEED
# ============================================================

async def seed() -> None:

    async with AsyncSessionLocal() as session:

        area_map = {}

        # ----------------------------------------------------
        # AREAS
        # ----------------------------------------------------

        for data in AREAS:

            area = await session.scalar(
                select(AdventureArea).where(
                    AdventureArea.name == data["name"]
                )
            )

            if area is None:

                area = AdventureArea(
                    name=data["name"],
                    description=data["description"],
                    recommended_level=data[
                        "recommended_level"
                    ],
                    min_level=data["min_level"],
                    max_level=data["max_level"],
                    is_active=True,
                )

                session.add(area)

                await session.flush()

                print(
                    f"✅ Area added: {area.name}"
                )

            else:

                area.description = data["description"]
                area.recommended_level = data[
                    "recommended_level"
                ]
                area.min_level = data["min_level"]
                area.max_level = data["max_level"]
                area.is_active = True

                print(
                    f"🔄 Area updated: {area.name}"
                )

            area_map[data["name"]] = area

        # ----------------------------------------------------
        # ENEMIES
        # ----------------------------------------------------

        for data in ENEMIES:

            area = area_map[data["area"]]

            (
                xp_reward,
                skill_xp_reward,
                gold_reward,
            ) = calculate_enemy_rewards(
                data["level"]
            )

            enemy = await session.scalar(
                select(AdventureEnemy).where(
                    AdventureEnemy.name == data["name"]
                )
            )

            if enemy is None:

                enemy = AdventureEnemy(
                    area_id=area.id,
                    name=data["name"],
                    description=data["description"],
                    level=data["level"],
                    hp=data["hp"],
                    attack=data["attack"],
                    defense=data["defense"],
                    xp_reward=xp_reward,
                    skill_xp_reward=skill_xp_reward,
                    gold_reward=gold_reward,
                    is_active=True,
                )

                session.add(enemy)

                print(
                    f"✅ Enemy added: {enemy.name}"
                )

            else:

                enemy.area_id = area.id
                enemy.description = data["description"]
                enemy.level = data["level"]
                enemy.hp = data["hp"]
                enemy.attack = data["attack"]
                enemy.defense = data["defense"]

                # پاداش‌ها خودکار محاسبه و به‌روزرسانی می‌شوند
                enemy.xp_reward = xp_reward
                enemy.skill_xp_reward = skill_xp_reward
                enemy.gold_reward = gold_reward

                enemy.is_active = True

                print(
                    f"🔄 Enemy updated: {enemy.name}"
                )

        await session.commit()

    # --------------------------------------------------------
    # REWARD REPORT
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("✅ Adventure seed completed successfully.")
    print("=" * 60)

    print()
    print("📊 Automatic Enemy Rewards")
    print("-" * 60)

    for data in ENEMIES:

        (
            xp_reward,
            skill_xp_reward,
            gold_reward,
        ) = calculate_enemy_rewards(
            data["level"]
        )

        print(
            f"{data['name']} | "
            f"Lv.{data['level']} | "
            f"✨ {xp_reward} XP | "
            f"🔮 {skill_xp_reward} Skill XP | "
            f"💰 {gold_reward} Gold"
        )


if __name__ == "__main__":
    asyncio.run(seed())