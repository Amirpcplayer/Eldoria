from __future__ import annotations

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.adventure import AdventureArea, AdventureEnemy
from models.character import Character
from services.monster_level_service import calculate_monster_level


async def get_character(
    telegram_id: int,
) -> Character | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )


async def get_active_areas() -> list[AdventureArea]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AdventureArea)
            .where(
                AdventureArea.is_active.is_(True)
            )
            .order_by(
                AdventureArea.min_level,
                AdventureArea.id,
            )
        )

        return list(result.scalars().all())


async def get_area(
    area_id: int,
) -> AdventureArea | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(AdventureArea).where(
                AdventureArea.id == area_id,
                AdventureArea.is_active.is_(True),
            )
        )


async def get_area_enemies(
    area_id: int,
) -> list[AdventureEnemy]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AdventureEnemy)
            .where(
                AdventureEnemy.area_id == area_id,
                AdventureEnemy.is_active.is_(True),
            )
            .order_by(
                AdventureEnemy.level,
                AdventureEnemy.id,
            )
        )

        return list(result.scalars().all())


async def get_enemy(
    enemy_id: int,
) -> AdventureEnemy | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(AdventureEnemy).where(
                AdventureEnemy.id == enemy_id,
                AdventureEnemy.is_active.is_(True),
            )
        )


def is_area_unlocked(
    character: Character,
    area: AdventureArea,
) -> bool:
    return character.level >= area.min_level


def get_effective_enemy_level(
    character: Character,
    enemy: AdventureEnemy,
    area: AdventureArea,
) -> int:
    return calculate_monster_level(
        character_level=character.level,
        enemy_level=enemy.level,
        area_min_level=area.min_level,
        area_max_level=area.max_level,
    )