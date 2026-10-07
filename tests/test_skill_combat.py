import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.character_skill import CharacterSkill
from models.skill import Skill

from services.skill_service import (
    get_skill_mana_cost,
    get_skill_power,
)


async def main() -> None:
    print("=" * 80)
    print("WORLD ELDORIA - SKILL COMBAT TEST")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character)
            .order_by(Character.id)
        )

        if character is None:
            print("❌ هیچ Characterای پیدا نشد.")
            return

        result = await session.execute(
            select(Skill, CharacterSkill)
            .join(
                CharacterSkill,
                CharacterSkill.skill_id == Skill.id,
            )
            .where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.unlocked.is_(True),
                Skill.is_active.is_(True),
            )
            .order_by(
                CharacterSkill.slot,
                Skill.id,
            )
        )

        skills = list(result.all())

    print()
    print("👤 PLAYER")
    print("-" * 80)
    print(f"Name={character.name}")
    print(f"Level={character.level}")
    print(f"Magic Power={character.magic_power}")
    print(f"Mana={character.mana}/{character.max_mana}")

    if not skills:
        print()
        print("❌ هیچ Skill فعال و Unlock شده‌ای پیدا نشد.")
        return

    print()
    print("=" * 80)
    print("🔮 SKILLS")
    print("=" * 80)

    for skill, character_skill in skills:
        skill_level = character_skill.level

        mana_cost = get_skill_mana_cost(
            skill,
            skill_level,
        )

        skill_power = get_skill_power(
            skill,
            skill_level,
        )

        print()
        print(f"Skill={skill.name}")
        print(f"Skill ID={skill.id}")
        print(f"Level={skill_level}")
        print(f"Mana Cost={mana_cost}")
        print(f"Skill Power={skill_power}")

    print()
    print("=" * 80)
    print("✅ SKILL DATA TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())