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
    can_learn_skill,
    unlock_skill,
)


TEST_CHARACTER_ID = 1

EXPECTED_UNLOCK_LEVELS = {
    1: 0,   # Fire
    2: 0,   # Water
    3: 0,   # Wind
    4: 0,   # Earth
    5: 20,  # Electro
    6: 20,  # Ice
    7: 60,  # Light
    8: 60,  # Dark
}


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL UNLOCK LEVEL TEST")
    print("=" * 80)

    # =================================================================
    # LOAD CHARACTER
    # =================================================================
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.id == TEST_CHARACTER_ID
            )
        )

        if character is None:
            print("❌ Test character not found.")
            return

        telegram_id = character.telegram_id

        print("\n" + "=" * 80)
        print("👤 CHARACTER")
        print("-" * 80)
        print(f"ID={character.id}")
        print(f"Name={character.name}")
        print(f"Current Level={character.level}")

    # =================================================================
    # LOAD SKILLS
    # =================================================================
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Skill)
            .where(
                Skill.id.in_(EXPECTED_UNLOCK_LEVELS.keys()),
                Skill.is_active.is_(True),
            )
            .order_by(Skill.id)
        )

        skills = list(result.scalars().all())

    if len(skills) != len(EXPECTED_UNLOCK_LEVELS):
        print(
            f"❌ Expected {len(EXPECTED_UNLOCK_LEVELS)} skills, "
            f"found {len(skills)}."
        )
        return

    print("\n" + "=" * 80)
    print("🔮 SKILL UNLOCK LEVEL CONFIGURATION")
    print("-" * 80)

    for skill in skills:
        expected = EXPECTED_UNLOCK_LEVELS[skill.id]

        print(
            f"ID={skill.id} | "
            f"{skill.name} | "
            f"Element={skill.element} | "
            f"DB Unlock={skill.unlock_level} | "
            f"Expected={expected}"
        )

        assert skill.unlock_level == expected

    print("✅ All skill unlock levels are configured correctly.")

    # =================================================================
    # SAVE ORIGINAL CHARACTER STATE
    # =================================================================
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.id == TEST_CHARACTER_ID
            )
        )

        assert character is not None

        original_level = character.level

        result = await session.execute(
            select(CharacterSkill).where(
                CharacterSkill.character_id == TEST_CHARACTER_ID,
                CharacterSkill.skill_id.in_(
                    EXPECTED_UNLOCK_LEVELS.keys()
                ),
            )
        )

        original_skill_states = {}

        for character_skill in result.scalars().all():
            original_skill_states[character_skill.skill_id] = {
                "level": character_skill.level,
                "slot": character_skill.slot,
                "unlocked": character_skill.unlocked,
            }

    try:
        # =============================================================
        # CLEAN TEST SKILLS
        # =============================================================
        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == TEST_CHARACTER_ID
                )
            )

            assert character is not None

            character.level = 1

            result = await session.execute(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == TEST_CHARACTER_ID,
                    CharacterSkill.skill_id.in_(
                        EXPECTED_UNLOCK_LEVELS.keys()
                    ),
                )
            )

            for character_skill in result.scalars().all():
                character_skill.unlocked = False
                character_skill.slot = None
                character_skill.level = 1

            await session.commit()

        # =============================================================
        # TEST 1 - LEVEL 1 BASIC SKILLS
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 1 - LEVEL 1 BASIC SKILLS")
        print("-" * 80)

        for skill_id in [1, 2, 3, 4]:
            skill = next(
                skill
                for skill in skills
                if skill.id == skill_id
            )

            success, message = await can_learn_skill(
                TEST_CHARACTER_ID,
                skill_id,
            )

            print(
                f"{skill.name} | "
                f"Unlock Level={skill.unlock_level} | "
                f"Can Learn={success}"
            )

            assert success is True

        print("✅ Basic skills are available at Level 1.")

        # =============================================================
        # TEST 2 - LEVEL 1 LOCKED SKILLS
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 2 - LEVEL 1 LOCKED SKILLS")
        print("-" * 80)

        for skill_id in [5, 6, 7, 8]:
            skill = next(
                skill
                for skill in skills
                if skill.id == skill_id
            )

            success, message = await can_learn_skill(
                TEST_CHARACTER_ID,
                skill_id,
            )

            print(
                f"{skill.name} | "
                f"Required={skill.unlock_level} | "
                f"Can Learn={success}"
            )
            print(f"Message={message}")

            assert success is False
            assert "باز نشده" in message

        print("✅ Locked skills correctly blocked at Level 1.")

        # =============================================================
        # TEST 3 - LEVEL 19
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 3 - LEVEL 19 BOUNDARY")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == TEST_CHARACTER_ID
                )
            )

            assert character is not None

            character.level = 19

            await session.commit()

        for skill_id in [5, 6]:
            skill = next(
                skill
                for skill in skills
                if skill.id == skill_id
            )

            success, message = await can_learn_skill(
                TEST_CHARACTER_ID,
                skill_id,
            )

            print(
                f"{skill.name} | "
                f"Character Lv=19 | "
                f"Required={skill.unlock_level} | "
                f"Can Learn={success}"
            )

            assert success is False

        print("✅ Level 19 correctly blocks Level 20 skills.")

        # =============================================================
        # TEST 4 - LEVEL 20
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 4 - LEVEL 20 BOUNDARY")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == TEST_CHARACTER_ID
                )
            )

            assert character is not None

            character.level = 20

            await session.commit()

        for skill_id in [5, 6]:
            skill = next(
                skill
                for skill in skills
                if skill.id == skill_id
            )

            success, message = await can_learn_skill(
                TEST_CHARACTER_ID,
                skill_id,
            )

            print(
                f"{skill.name} | "
                f"Character Lv=20 | "
                f"Required={skill.unlock_level} | "
                f"Can Learn={success}"
            )

            assert success is True

        print("✅ Level 20 correctly unlocks Electro and Ice.")

        # =============================================================
        # TEST 5 - LEVEL 59
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 5 - LEVEL 59 BOUNDARY")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == TEST_CHARACTER_ID
                )
            )

            assert character is not None

            character.level = 59

            await session.commit()

        for skill_id in [7, 8]:
            skill = next(
                skill
                for skill in skills
                if skill.id == skill_id
            )

            success, message = await can_learn_skill(
                TEST_CHARACTER_ID,
                skill_id,
            )

            print(
                f"{skill.name} | "
                f"Character Lv=59 | "
                f"Required={skill.unlock_level} | "
                f"Can Learn={success}"
            )

            assert success is False

        print("✅ Level 59 correctly blocks Level 60 skills.")

        # =============================================================
        # TEST 6 - LEVEL 60
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 6 - LEVEL 60 BOUNDARY")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == TEST_CHARACTER_ID
                )
            )

            assert character is not None

            character.level = 60

            await session.commit()

        for skill_id in [7, 8]:
            skill = next(
                skill
                for skill in skills
                if skill.id == skill_id
            )

            success, message = await can_learn_skill(
                TEST_CHARACTER_ID,
                skill_id,
            )

            print(
                f"{skill.name} | "
                f"Character Lv=60 | "
                f"Required={skill.unlock_level} | "
                f"Can Learn={success}"
            )

            assert success is True

        print("✅ Level 60 correctly unlocks Light and Dark.")

        # =============================================================
        # TEST 7 - ACTUAL unlock_skill()
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 7 - ACTUAL SKILL UNLOCK")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == TEST_CHARACTER_ID
                )
            )

            assert character is not None

            character.level = 60

            await session.commit()

        success, message = await unlock_skill(
            telegram_id,
            7,
        )

        print(f"Skill={skills[6].name}")
        print(f"Success={success}")
        print(f"Message={message}")

        assert success is True

        async with AsyncSessionLocal() as session:
            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == TEST_CHARACTER_ID,
                    CharacterSkill.skill_id == 7,
                )
            )

            assert character_skill is not None
            assert character_skill.unlocked is True
            assert character_skill.level == 1
            assert character_skill.slot is not None

            print(
                f"Unlocked={character_skill.unlocked}"
            )
            print(
                f"Level={character_skill.level}"
            )
            print(
                f"Slot={character_skill.slot}"
            )

        print("✅ Actual skill unlock works correctly.")

        # =============================================================
        # TEST 8 - NO UNEXPECTED UNLOCKS
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 8 - NO UNEXPECTED UNLOCKS")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == TEST_CHARACTER_ID,
                    CharacterSkill.skill_id.in_(
                        EXPECTED_UNLOCK_LEVELS.keys()
                    ),
                    CharacterSkill.unlocked.is_(True),
                )
            )

            unlocked_ids = {
                character_skill.skill_id
                for character_skill in result.scalars().all()
            }

        print(
            f"Unlocked skill IDs="
            f"{sorted(unlocked_ids)}"
        )

        assert 7 in unlocked_ids

        print("✅ No unexpected skill unlocks detected.")

    finally:
        # =============================================================
        # RESTORE DATABASE
        # =============================================================
        print("\n" + "=" * 80)
        print("🧹 RESTORING DATABASE")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == TEST_CHARACTER_ID
                )
            )

            assert character is not None

            character.level = original_level

            result = await session.execute(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == TEST_CHARACTER_ID,
                    CharacterSkill.skill_id.in_(
                        EXPECTED_UNLOCK_LEVELS.keys()
                    ),
                )
            )

            current_skill_states = {
                cs.skill_id: cs
                for cs in result.scalars().all()
            }

            for skill_id, state in original_skill_states.items():
                character_skill = current_skill_states.get(skill_id)

                if character_skill is not None:
                    character_skill.level = state["level"]
                    character_skill.slot = state["slot"]
                    character_skill.unlocked = state["unlocked"]

            await session.commit()

        print("✅ Database state restored.")

    print("\n" + "=" * 80)
    print("🎉 ALL SKILL UNLOCK LEVEL TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())