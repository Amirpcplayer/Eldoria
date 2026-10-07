import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character

from services.adventure_service import (
    get_area,
    get_area_enemies,
    get_effective_enemy_level,
)


async def get_first_character() -> Character | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character)
            .order_by(Character.id)
        )


async def main():
    character = await get_first_character()

    if character is None:
        print("❌ No character found in database")
        return

    area = await get_area(1)

    if area is None:
        print("❌ Area not found")
        return

    enemies = await get_area_enemies(area.id)

    print("=" * 80)
    print("WORLD ELDORIA - ADVENTURE SCALING TEST")
    print("=" * 80)

    print(
        f"Character: {character.name} | "
        f"Character ID={character.id} | "
        f"Level={character.level}"
    )

    print(
        f"Area: {area.name} | "
        f"Level Range={area.min_level}-{area.max_level}"
    )

    print("-" * 80)

    for enemy in enemies:
        effective_level = get_effective_enemy_level(
            character,
            enemy,
            area,
        )

        print(
            f"{enemy.name} | "
            f"Base Level={enemy.level} | "
            f"Effective Level={effective_level} | "
            f"Monster ID={enemy.monster_id}"
        )

    print("=" * 80)
    print("✅ ADVENTURE SCALING TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())