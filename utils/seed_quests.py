import asyncio
import sys
from pathlib import Path

# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import select

from database.database import AsyncSessionLocal

from models.quest import Quest
from models.adventure import AdventureEnemy
from models.skill import Skill


# ============================================================
# QUEST DATA
# ============================================================

QUESTS = [
    {
        "name": "🌲 اولین شکار",
        "description": "اولین گرگ وحشی خود را شکست دهید.",
        "category": "story",
        "objective_type": "kill_enemy",
        "target_name": "🐺 گرگ وحشی",
        "required_amount": 1,
        "min_level": 1,
        "reward_xp": 250,
        "reward_skill_xp": 50,
        "reward_gold": 100,
        "is_repeatable": False,
    },
    {
        "name": "👺 شکارچی گابلین‌ها",
        "description": "سه گابلین را شکست دهید.",
        "category": "story",
        "objective_type": "kill_enemy",
        "target_name": "👺 گابلین",
        "required_amount": 3,
        "min_level": 1,
        "reward_xp": 500,
        "reward_skill_xp": 100,
        "reward_gold": 250,
        "is_repeatable": False,
    },
    {
        "name": "📈 مسیر قهرمان",
        "description": "به سطح 5 برسید.",
        "category": "story",
        "objective_type": "level",
        "target_name": None,
        "required_amount": 5,
        "min_level": 1,
        "reward_xp": 750,
        "reward_skill_xp": 150,
        "reward_gold": 300,
        "is_repeatable": False,
    },
    {
        "name": "🔥 آغاز جادو",
        "description": "جادوی آتش را یاد بگیرید.",
        "category": "story",
        "objective_type": "learn_skill",
        "target_name": "🔥 جادوی آتش",
        "required_amount": 1,
        "min_level": 1,
        "reward_xp": 500,
        "reward_skill_xp": 200,
        "reward_gold": 200,
        "is_repeatable": False,
    },
    {
        "name": "⚔️ شکار روزانه",
        "description": "پنج دشمن را شکست دهید.",
        "category": "daily",
        "objective_type": "kill_enemy",
        "target_name": None,
        "required_amount": 5,
        "min_level": 1,
        "reward_xp": 400,
        "reward_skill_xp": 75,
        "reward_gold": 200,
        "is_repeatable": True,
    },
    {
        "name": "💀 جنگجوی باتجربه",
        "description": "بیست دشمن را شکست دهید.",
        "category": "achievement",
        "objective_type": "kill_enemy",
        "target_name": None,
        "required_amount": 20,
        "min_level": 1,
        "reward_xp": 1500,
        "reward_skill_xp": 300,
        "reward_gold": 750,
        "is_repeatable": False,
    },
    {
        "name": "👑 قهرمان اِلدوریا",
        "description": "به سطح 20 برسید.",
        "category": "achievement",
        "objective_type": "level",
        "target_name": None,
        "required_amount": 20,
        "min_level": 1,
        "reward_xp": 5000,
        "reward_skill_xp": 1000,
        "reward_gold": 2500,
        "is_repeatable": False,
    },
]


# ============================================================
# HELPERS
# ============================================================

async def find_enemy(
    session,
    name: str | None,
):
    if not name:
        return None

    return await session.scalar(
        select(AdventureEnemy).where(
            AdventureEnemy.name == name
        )
    )


async def find_skill(
    session,
    name: str | None,
):
    if not name:
        return None

    return await session.scalar(
        select(Skill).where(
            Skill.name == name
        )
    )


async def find_existing_quest(
    session,
    name: str,
):
    return await session.scalar(
        select(Quest).where(
            Quest.name == name
        )
    )


# ============================================================
# SEED
# ============================================================

async def seed_quests():
    print()
    print("========================================")
    print("       WORLD ELDORIA QUEST SEED")
    print("========================================")
    print()

    print("[1/3] Connecting to database...")

    async with AsyncSessionLocal() as session:

        print("      PASS - Database connection ready.")
        print()

        print("[2/3] Checking existing quests...")

        created = 0
        skipped = 0

        for data in QUESTS:

            existing = await find_existing_quest(
                session,
                data["name"],
            )

            if existing is not None:
                skipped += 1
                continue

            target_id = None

            # ------------------------------------------------
            # Enemy target
            # ------------------------------------------------

            if data["objective_type"] == "kill_enemy":

                enemy = await find_enemy(
                    session,
                    data["target_name"],
                )

                if data["target_name"] and enemy is None:
                    raise RuntimeError(
                        "Required enemy was not found: "
                        f"{data['target_name']}"
                    )

                if enemy is not None:
                    target_id = enemy.id

            # ------------------------------------------------
            # Skill target
            # ------------------------------------------------

            elif data["objective_type"] == "learn_skill":

                skill = await find_skill(
                    session,
                    data["target_name"],
                )

                if skill is None:
                    raise RuntimeError(
                        "Required skill was not found: "
                        f"{data['target_name']}"
                    )

                target_id = skill.id

            # ------------------------------------------------
            # Level target
            # ------------------------------------------------

            elif data["objective_type"] == "level":

                target_id = data["required_amount"]

            # ------------------------------------------------
            # Create Quest
            # ------------------------------------------------

            quest = Quest(
                name=data["name"],
                description=data["description"],
                category=data["category"],
                objective_type=data["objective_type"],
                target_id=target_id,
                required_amount=data["required_amount"],
                min_level=data["min_level"],
                reward_xp=data["reward_xp"],
                reward_skill_xp=data["reward_skill_xp"],
                reward_gold=data["reward_gold"],
                reward_equipment_id=None,
                is_repeatable=data["is_repeatable"],
                is_active=True,
            )

            session.add(quest)

            created += 1

        await session.commit()

        print(
            f"      PASS - Existing quests: {skipped}"
        )

        print()

        print("[3/3] Creating missing quests...")

        print(
            f"      Created: {created}"
        )

        print(
            f"      Skipped: {skipped}"
        )

        print()

        print("========================================")
        print("       QUEST SEED COMPLETED")
        print("========================================")
        print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(seed_quests())