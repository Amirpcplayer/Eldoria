import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.adventure import AdventureEnemy
from models.monster import Monster

from services.character_stats_service import (
    calculate_character_combat_stats,
)
from services.monster_level_service import (
    calculate_monster_level,
)
from services.monster_stats_service import (
    calculate_monster_stats,
)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character)
            .order_by(Character.id)
        )

        enemy_result = await session.execute(
            select(
                AdventureEnemy,
                Monster,
            )
            .join(
                Monster,
                AdventureEnemy.monster_id == Monster.id,
            )
            .order_by(
                AdventureEnemy.id,
            )
            .limit(3)
        )

        enemies = enemy_result.all()

    print("=" * 80)
    print("WORLD ELDORIA - COMBAT STATS TEST")
    print("=" * 80)

    if character is None:
        print("❌ هیچ Characterای در دیتابیس وجود ندارد.")
        return

    stats = await calculate_character_combat_stats(
        character
    )

    print()
    print("👤 PLAYER")
    print("-" * 80)

    print(
        f"Name={character.name} | "
        f"Level={character.level}"
    )

    print(
        f"❤️ HP={stats.hp}/{stats.max_hp}"
    )

    print(
        f"🔵 Mana={stats.mana}/{stats.max_mana}"
    )

    print(
        f"⚔️ ATK={stats.attack}"
    )

    print(
        f"🔮 Magic Power={stats.magic_power}"
    )

    print(
        f"🛡️ DEF={stats.defense}"
    )

    print(
        f"🔮 MDEF={stats.magic_defense}"
    )

    print(
        f"💨 Speed={stats.speed}"
    )

    print(
        f"🎯 Accuracy={stats.accuracy}"
    )

    print(
        f"🍀 Luck={stats.luck}"
    )

    print(
        f"💥 Critical={stats.critical}"
    )

    print()
    print("=" * 80)
    print("👹 MONSTER TEST")
    print("=" * 80)

    if not enemies:
        print("❌ هیچ Monster متصل به AdventureEnemy پیدا نشد.")
        return

    for enemy, monster in enemies:
        effective_level = calculate_monster_level(
            character_level=character.level,
            enemy_level=enemy.level,
            area_min_level=1,
            area_max_level=100,
        )

        monster_stats = calculate_monster_stats(
            monster=monster,
            level=effective_level,
        )

        print()
        print(
            f"👹 {monster.name} "
            f"| Variant={monster.variant}"
        )

        print(
            f"Level={effective_level} | "
            f"Tier={monster.tier} | "
            f"Element={monster.element}"
        )

        print(
            f"❤️ HP={monster_stats.hp}"
        )

        print(
            f"⚔️ ATK={monster_stats.attack}"
        )

        print(
            f"🛡️ DEF={monster_stats.defense}"
        )

        print(
            f"🔮 MDEF={monster_stats.magic_defense}"
        )

    print()
    print("=" * 80)
    print("✅ COMBAT STATS TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())