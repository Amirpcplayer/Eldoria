import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.monster import Monster

from services.adventure_service import (
    get_area,
    get_area_enemies,
    get_effective_enemy_level,
)
from services.monster_stats_service import calculate_monster_stats


async def get_first_character() -> Character | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character).order_by(Character.id)
        )


async def get_monster(monster_id: int) -> Monster | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Monster).where(Monster.id == monster_id)
        )


async def main():
    character = await get_first_character()

    if character is None:
        print("❌ No character found")
        return

    area = await get_area(1)

    if area is None:
        print("❌ Area not found")
        return

    enemies = await get_area_enemies(area.id)

    print("=" * 100)
    print("WORLD ELDORIA - ADVENTURE → MONSTER INTEGRATION TEST")
    print("=" * 100)

    print(
        f"👤 Character: {character.name} | "
        f"Level={character.level}"
    )

    print(
        f"📍 Area: {area.name} | "
        f"Level Range={area.min_level}-{area.max_level}"
    )

    print("-" * 100)

    for enemy in enemies:
        if enemy.monster_id is None:
            print(
                f"❌ {enemy.name}: monster_id is NULL"
            )
            continue

        monster = await get_monster(enemy.monster_id)

        if monster is None:
            print(
                f"❌ {enemy.name}: "
                f"Monster ID {enemy.monster_id} not found"
            )
            continue

        effective_level = get_effective_enemy_level(
            character,
            enemy,
            area,
        )

        stats = calculate_monster_stats(
            monster,
            effective_level,
        )

        print(
            f"👹 {enemy.name}\n"
            f"   Variant={monster.variant} | "
            f"Tier={monster.tier} | "
            f"Element={monster.element}\n"
            f"   Base Level={enemy.level} | "
            f"Effective Level={effective_level}\n"
            f"   HP={stats.hp} | "
            f"ATK={stats.attack} | "
            f"Magic={stats.magic_power} | "
            f"DEF={stats.defense} | "
            f"MDEF={stats.magic_defense}\n"
            f"   SPD={stats.speed} | "
            f"ACC={stats.accuracy} | "
            f"LUCK={stats.luck} | "
            f"CRIT={stats.critical}"
        )

        print("-" * 100)

    print("✅ ADVENTURE → MONSTER INTEGRATION TEST COMPLETED")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
    