import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.adventure import AdventureEnemy
from models.monster import Monster


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AdventureEnemy, Monster)
            .outerjoin(
                Monster,
                AdventureEnemy.monster_id == Monster.id,
            )
            .order_by(
                AdventureEnemy.id,
            )
        )

        rows = result.all()

    print("=" * 80)
    print("WORLD ELDORIA - ADVENTURE MONSTER LINKS")
    print("=" * 80)

    if not rows:
        print("❌ هیچ AdventureEnemyای در دیتابیس وجود ندارد.")
        return

    linked_count = 0
    unlinked_count = 0

    for enemy, monster in rows:
        if monster is None:
            print(
                f"❌ ID={enemy.id} | "
                f"{enemy.name} | "
                f"Monster=None"
            )
            unlinked_count += 1
            continue

        print(
            f"✅ Enemy ID={enemy.id} | "
            f"{enemy.name} | "
            f"Monster ID={monster.id} | "
            f"Variant={monster.variant} | "
            f"Element={monster.element} | "
            f"Tier={monster.tier}"
        )

        linked_count += 1

    print("-" * 80)
    print(f"Total Adventure Enemies: {len(rows)}")
    print(f"Linked: {linked_count}")
    print(f"Unlinked: {unlinked_count}")

    if unlinked_count == 0:
        print("✅ تمام AdventureEnemyها به Monster متصل هستند.")
    else:
        print("❌ بعضی AdventureEnemyها هنوز Monster ندارند.")


if __name__ == "__main__":
    asyncio.run(main())