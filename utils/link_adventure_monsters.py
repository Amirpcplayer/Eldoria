import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.adventure import AdventureEnemy
from models.monster import Monster


ADVENTURE_TO_MONSTER = {
    "🐺 گرگ وحشی": "normal_wolf",
    "👺 گابلین": "goblin",
    "🗡️ راهزن جنگل": "forest_bandit",
    "🪨 گولم سنگی": "stone_golem",
    "🐻 خرس کوهستانی": "mountain_bear",
    "🦂 عقرب غول‌پیکر": "giant_scorpion",
    "🐍 مار شنی": "sand_serpent",
    "🔥 گولم آتشین": "fire_golem",
    "🐉 دریک آتشین": "fire_drake",
    "👻 روح تاریک": "dark_spirit",
    "😈 شیطان سایه": "shadow_demon",
    "🦄 موجود افسانه‌ای": "legendary_creature",
    "🐲 اژدهای باستانی": "ancient_dragon",
}


async def link_adventure_monsters() -> int:
    linked = 0

    async with AsyncSessionLocal() as session:
        for enemy_name, monster_variant in ADVENTURE_TO_MONSTER.items():
            enemy = await session.scalar(
                select(AdventureEnemy).where(
                    AdventureEnemy.name == enemy_name
                )
            )

            if enemy is None:
                raise RuntimeError(f"AdventureEnemy not found: {enemy_name}; no links committed")

            monster = await session.scalar(
                select(Monster).where(
                    Monster.variant == monster_variant
                )
            )

            if monster is None:
                raise RuntimeError(f"Monster not found: {monster_variant}; no links committed")

            enemy.monster_id = monster.id

            print(
                f"✅ {enemy.name} "
                f"-> {monster.variant} "
                f"(Monster ID={monster.id})"
            )

            linked += 1

        await session.commit()

    return linked


async def main():
    count = await link_adventure_monsters()

    print()
    print("=" * 60)
    print(
        f"Adventure Monster linking completed: "
        f"{count} enemies linked."
    )
    print("=" * 60)


if __name__ == "__main__":
    from utils.script_runtime import run_script
    run_script(main)