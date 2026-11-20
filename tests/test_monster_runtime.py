import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.adventure import AdventureArea, AdventureEnemy
from models.monster import Monster

from services.monster_level_service import calculate_monster_level
from services.monster_stats_service import calculate_monster_stats


TEST_LEVELS = [1, 3, 5, 10, 20, 35, 50, 70, 90]


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                AdventureEnemy,
                AdventureArea,
                Monster,
            )
            .join(
                AdventureArea,
                AdventureEnemy.area_id == AdventureArea.id,
            )
            .join(
                Monster,
                AdventureEnemy.monster_id == Monster.id,
            )
            .order_by(
                AdventureEnemy.id,
            )
        )

        rows = result.all()

    print("=" * 100)
    print("WORLD ELDORIA - MONSTER RUNTIME TEST")
    print("=" * 100)

    if not rows:
        print("❌ هیچ Monster متصل به AdventureEnemy پیدا نشد.")
        return

    for enemy, area, monster in rows:
        print()
        print("-" * 100)

        print(
            f"👹 {enemy.name} | "
            f"Variant={monster.variant} | "
            f"Tier={monster.tier} | "
            f"Element={monster.element}"
        )

        print(
            f"📍 Area: {area.name} | "
            f"Area Level={area.min_level}-{area.max_level} | "
            f"Base Enemy Level={enemy.level}"
        )

        print(
            f"⚙️ Multiplier={monster.power_multiplier}"
        )

        for character_level in TEST_LEVELS:
            # فقط Levelهایی را تست می‌کنیم که وارد منطقه شده‌اند.
            if character_level < area.min_level:
                continue

            effective_level = calculate_monster_level(
                character_level=character_level,
                enemy_level=enemy.level,
                area_min_level=area.min_level,
                area_max_level=area.max_level,
            )

            stats = calculate_monster_stats(
                monster=monster,
                level=effective_level,
            )

            print(
                f"Player Lv.{character_level:>2} "
                f"→ Monster Lv.{effective_level:>2} | "
                f"HP={stats.hp:<6} "
                f"ATK={stats.attack:<5} "
                f"DEF={stats.defense:<5} "
                f"MDEF={stats.magic_defense:<5}"
            )

    print()
    print("=" * 100)
    print("✅ Monster runtime test completed successfully.")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())