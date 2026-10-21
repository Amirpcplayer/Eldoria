"""One-time, safe stat rescale for characters created before the endgame curve update.

Run from the project root after installing the update:
    python -m utils.rebalance_existing_characters

Current HP/Mana ratios are preserved; defeated characters remain at zero HP.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from services.xp_service import get_base_stats_for_level


async def rebalance_existing_characters() -> None:
    updated = 0
    async with AsyncSessionLocal() as session:
        characters = list((await session.scalars(select(Character))).all())
        for character in characters:
            level = max(1, min(100, int(character.level or 1)))
            stats = get_base_stats_for_level(level)
            old_hp_max = max(1, int(character.max_hp or 100))
            old_mana_max = max(1, int(character.max_mana or 100))
            old_hp = max(0, int(character.hp or 0))
            old_mana = max(0, int(character.mana or 0))

            hp_ratio = min(1.0, old_hp / old_hp_max)
            mana_ratio = min(1.0, old_mana / old_mana_max)

            character.max_hp = stats["max_hp"]
            character.max_mana = stats["max_mana"]
            character.hp = 0 if old_hp <= 0 else min(stats["max_hp"], max(1, int(stats["max_hp"] * hp_ratio)))
            character.mana = 0 if old_mana <= 0 else min(stats["max_mana"], max(1, int(stats["max_mana"] * mana_ratio)))
            character.attack = stats["attack"]
            character.magic_power = stats["magic_power"]
            character.defense = stats["defense"]
            character.magic_defense = stats["magic_defense"]
            character.speed = stats["speed"]
            character.accuracy = stats["accuracy"]
            character.luck = stats["luck"]
            character.critical = stats["critical"]
            updated += 1
        await session.commit()
    print(f"✅ Rebalanced {updated} characters. Current HP/Mana ratios were preserved.")


if __name__ == "__main__":
    asyncio.run(rebalance_existing_characters())
