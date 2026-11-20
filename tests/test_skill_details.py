import asyncio
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.character_skill import CharacterSkill
from models.skill import Skill

from services.skill_service import (
    get_skill_details,
    get_skill_power,
    get_skill_mana_cost,
)


TEST_CHARACTER_NAME = "Anos Voldigoad"
LEARNED_SKILL_ID = 1
UNLEARNED_SKILL_ID = 2


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL DETAILS TEST")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.name == TEST_CHARACTER_NAME
            )
        )

        if character is None:
            print("❌ Character not found.")
            return

        print("\n" + "=" * 80)
        print("👤 CHARACTER")
        print("-" * 80)
        print(f"ID={character.id}")
        print(f"Name={character.name}")
        print(f"Level={character.level}")
        print(f"Skill XP={character.skill_xp}")
        print(f"Gold={character.gold}")

        original_states = {}

        for skill_id in (LEARNED_SKILL_ID, UNLEARNED_SKILL_ID):
            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id,
                    CharacterSkill.skill_id == skill_id,
                )
            )

            if character_skill is not None:
                original_states[skill_id] = {
                    "id": character_skill.id,
                    "level": character_skill.level,
                    "slot": character_skill.slot,
                    "unlocked": character_skill.unlocked,
                }

        learned_character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == LEARNED_SKILL_ID,
            )
        )

        if learned_character_skill is None:
            learned_character_skill = CharacterSkill(
                character_id=character.id,
                skill_id=LEARNED_SKILL_ID,
                level=3,
                slot=1,
                unlocked=True,
            )
            session.add(learned_character_skill)
        else:
            learned_character_skill.level = 3
            learned_character_skill.slot = 1
            learned_character_skill.unlocked = True

        unlearned_character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == UNLEARNED_SKILL_ID,
            )
        )

        if unlearned_character_skill is not None:
            unlearned_character_skill.unlocked = False
            unlearned_character_skill.slot = None

        await session.commit()

    # ================================================================
    # TEST 1 - Learned skill
    # ================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 1 - LEARNED SKILL")
    print("-" * 80)

    details = await get_skill_details(
        character.id,
        LEARNED_SKILL_ID,
    )

    assert details is not None

    skill = details["skill"]
    character_skill = details["character_skill"]

    expected_power = get_skill_power(skill, 3)
    expected_mana = get_skill_mana_cost(skill, 3)

    print(f"Skill={skill.name}")
    print(f"Element={skill.element}")
    print(f"Learned={details['learned']}")
    print(f"Level={details['level']}")
    print(f"Power={details['power']}")
    print(f"Mana Cost={details['mana_cost']}")

    assert details["learned"] is True
    assert character_skill is not None
    assert details["level"] == 3
    assert details["power"] == expected_power
    assert details["mana_cost"] == expected_mana

    print("✅ Learned skill details correct.")

    # ================================================================
    # TEST 2 - Unlearned skill
    # ================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 2 - UNLEARNED SKILL")
    print("-" * 80)

    details = await get_skill_details(
        character.id,
        UNLEARNED_SKILL_ID,
    )

    assert details is not None

    skill = details["skill"]

    print(f"Skill={skill.name}")
    print(f"Element={skill.element}")
    print(f"Learned={details['learned']}")
    print(f"Level={details['level']}")
    print(f"Power={details['power']}")
    print(f"Mana Cost={details['mana_cost']}")

    assert details["learned"] is False
    assert details["level"] == 1
    assert details["power"] == get_skill_power(skill, 1)
    assert details["mana_cost"] == get_skill_mana_cost(skill, 1)

    print("✅ Unlearned skill details correct.")

    # ================================================================
    # TEST 3 - Skill level scaling
    # ================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 3 - SKILL LEVEL SCALING")
    print("-" * 80)

    async with AsyncSessionLocal() as session:
        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == LEARNED_SKILL_ID,
            )
        )

        assert character_skill is not None

        character_skill.level = 5
        character_skill.unlocked = True
        character_skill.slot = 1

        await session.commit()

    details = await get_skill_details(
        character.id,
        LEARNED_SKILL_ID,
    )

    assert details is not None

    skill = details["skill"]

    expected_power = get_skill_power(skill, 5)
    expected_mana = get_skill_mana_cost(skill, 5)

    print(f"Skill={skill.name}")
    print(f"Level={details['level']}")
    print(f"Power={details['power']}")
    print(f"Expected Power={expected_power}")
    print(f"Mana Cost={details['mana_cost']}")
    print(f"Expected Mana Cost={expected_mana}")

    assert details["learned"] is True
    assert details["level"] == 5
    assert details["power"] == expected_power
    assert details["mana_cost"] == expected_mana

    print("✅ Skill level scaling correct.")

    # ================================================================
    # TEST 4 - Invalid skill
    # ================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 4 - INVALID SKILL ID")
    print("-" * 80)

    invalid_details = await get_skill_details(
        character.id,
        999999,
    )

    print(f"Result={invalid_details}")

    assert invalid_details is None

    print("✅ Invalid skill ID correctly returns None.")

    # ================================================================
    # TEST 5 - Inactive skill
    # ================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 5 - INACTIVE SKILL")
    print("-" * 80)

    inactive_skill_id = None

    async with AsyncSessionLocal() as session:
        inactive_skill = Skill(
            name="__TEST_INACTIVE_SKILL__",
            description="Temporary test skill",
            element="fire",
            skill_type="magic",
            target_type="single",
            rarity="common",
            max_level=10,
            base_power=100,
            power_per_level=10,
            mana_cost=10,
            cooldown=5,
            unlock_level=1,
            is_active=False,
        )

        session.add(inactive_skill)
        await session.flush()

        inactive_skill_id = inactive_skill.id

        await session.commit()

    try:
        inactive_details = await get_skill_details(
            character.id,
            inactive_skill_id,
        )

        print(f"Inactive Skill ID={inactive_skill_id}")
        print(f"Result={inactive_details}")

        assert inactive_details is None

        print("✅ Inactive skill correctly returns None.")

    finally:
        async with AsyncSessionLocal() as session:
            inactive_skill = await session.scalar(
                select(Skill).where(
                    Skill.id == inactive_skill_id
                )
            )

            if inactive_skill is not None:
                await session.delete(inactive_skill)
                await session.commit()

    # ================================================================
    # TEST 6 - Restore database
    # ================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 6 - DATABASE RESTORE")
    print("-" * 80)

    async with AsyncSessionLocal() as session:
        for skill_id in (LEARNED_SKILL_ID, UNLEARNED_SKILL_ID):
            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id,
                    CharacterSkill.skill_id == skill_id,
                )
            )

            original = original_states.get(skill_id)

            if original is None:
                if character_skill is not None:
                    await session.delete(character_skill)
            else:
                if character_skill is None:
                    character_skill = CharacterSkill(
                        id=original["id"],
                        character_id=character.id,
                        skill_id=skill_id,
                    )
                    session.add(character_skill)

                character_skill.level = original["level"]
                character_skill.slot = original["slot"]
                character_skill.unlocked = original["unlocked"]

        await session.commit()

    print("✅ Database state restored.")

    print("\n" + "=" * 80)
    print("🎉 ALL SKILL DETAILS TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())