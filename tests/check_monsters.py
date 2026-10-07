import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.monster import Monster


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Monster).order_by(
                Monster.family,
                Monster.id,
            )
        )

        monsters = list(result.scalars().all())

    print("=" * 70)
    print("WORLD ELDORIA MONSTERS")
    print("=" * 70)

    if not monsters:
        print("❌ هیچ Monsterای در دیتابیس وجود ندارد.")
        return

    for monster in monsters:
        print(
            f"ID={monster.id} | "
            f"Family={monster.family} | "
            f"Variant={monster.variant} | "
            f"Name={monster.name} | "
            f"Tier={monster.tier} | "
            f"Element={monster.element} | "
            f"Multiplier={monster.power_multiplier}"
        )

    print("-" * 70)
    print(f"Total monsters: {len(monsters)}")


if __name__ == "__main__":
    asyncio.run(main())