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
    get_unlocked_skill_slots,
    get_used_skill_slots,
)


TEST_CHARACTER_NAME = "Anos Voldigoad"

SKILL_1_ID = 1
SKILL_2_ID = 2
SKILL_3_ID = 3
SKILL_4_ID = 4


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL LEARN FLOW TEST")
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

        # ------------------------------------------------------------
        # Save original character state
        # ------------------------------------------------------------
        original_level = character.level

        original_states = {}

        for skill_id in (
            SKILL_1_ID,
            SKILL_2_ID,
            SKILL_3_ID,
            SKILL_4_ID,
        ):
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

    try:
        # ============================================================
        # TEST 1 - Slot rules
        # ============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 1 - SKILL SLOT RULES")
        print("-" * 80)

        assert get_unlocked_skill_slots(1) == 1
        assert get_unlocked_skill_slots(19) == 1
        assert get_unlocked_skill_slots(20) == 2
        assert get_unlocked_skill_slots(59) == 2
        assert get_unlocked_skill_slots(60) == 3
        assert get_unlocked_skill_slots(100) == 3

        print("Level 1  -> 1 slot ✅")
        print("Level 19 -> 1 slot ✅")
        print("Level 20 -> 2 slots ✅")
        print("Level 59 -> 2 slots ✅")
        print("Level 60 -> 3 slots ✅")
        print("Level 100 -> 3 slots ✅")

        # ============================================================
        # TEST 2 - Prepare Level 5 character
        # ============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 2 - PREPARE TEST CHARACTER")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.name == TEST_CHARACTER_NAME
                )
            )

            assert character is not None

            character.level = 5

            # Temporarily clear test skills
            result = await session.execute(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id,
                    CharacterSkill.skill_id.in_(
                        [
                            SKILL_1_ID,
                            SKILL_2_ID,
                            SKILL_3_ID,
                            SKILL_4_ID,
                        ]
                    ),
                )
            )

            for character_skill in result.scalars().all():
                character_skill.unlocked = False
                character_skill.slot = None

            await session.commit()

        used_slots = await get_used_skill_slots(character.id)

        assert used_slots == 0

        print("Character Level=5")
        print("Used Skill Slots=0")
        print("Max Skill Slots=1")
        print("✅ Test character prepared.")

        # ============================================================
        # TEST 3 - Learn first skill
        # ============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 3 - LEARN FIRST SKILL")
        print("-" * 80)

        can_learn, message = await can_learn_skill(
            character.id,
            SKILL_1_ID,
        )

        print(f"Can Learn={can_learn}")
        print(f"Message={message}")

        assert can_learn is True

        success, message = await unlock_skill(
            character.telegram_id,
            SKILL_1_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is True

        async with AsyncSessionLocal() as session:
            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id,
                    CharacterSkill.skill_id == SKILL_1_ID,
                )
            )

            assert character_skill is not None
            assert character_skill.unlocked is True
            assert character_skill.level == 1
            assert character_skill.slot == 1

        used_slots = await get_used_skill_slots(character.id)

        assert used_slots == 1

        print("Slot=1")
        print("Level=1")
        print("Unlocked=True")
        print("Used Slots=1")
        print("✅ First skill learned correctly.")

        # ============================================================
        # TEST 4 - Duplicate learning blocked
        # ============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 4 - DUPLICATE LEARNING")
        print("-" * 80)

        can_learn, message = await can_learn_skill(
            character.id,
            SKILL_1_ID,
        )

        print(f"Can Learn={can_learn}")
        print(f"Message={message}")

        assert can_learn is False

        success, message = await unlock_skill(
            character.telegram_id,
            SKILL_1_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is False

        print("✅ Duplicate skill learning correctly blocked.")

        # ============================================================
        # TEST 5 - Full slot blocked
        # ============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 5 - FULL SLOT BLOCK")
        print("-" * 80)

        can_learn, message = await can_learn_skill(
            character.id,
            SKILL_2_ID,
        )

        print(f"Can Learn Skill 2={can_learn}")
        print(f"Message={message}")

        assert can_learn is False

        success, message = await unlock_skill(
            character.telegram_id,
            SKILL_2_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is False

        used_slots = await get_used_skill_slots(character.id)

        assert used_slots == 1

        print("Used Slots=1/1")
        print("✅ Full slot correctly blocks second skill.")

        # ============================================================
        # TEST 6 - Level 20 unlocks second slot
        # ============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 6 - SECOND SLOT AT LEVEL 20")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == character.id
                )
            )

            assert character is not None

            character.level = 20

            await session.commit()

        max_slots = get_unlocked_skill_slots(20)

        assert max_slots == 2

        can_learn, message = await can_learn_skill(
            character.id,
            SKILL_2_ID,
        )

        print(f"Character Level=20")
        print(f"Max Slots={max_slots}")
        print(f"Can Learn Skill 2={can_learn}")
        print(f"Message={message}")

        assert can_learn is True

        success, message = await unlock_skill(
            character.telegram_id,
            SKILL_2_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is True

        async with AsyncSessionLocal() as session:
            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id,
                    CharacterSkill.skill_id == SKILL_2_ID,
                )
            )

            assert character_skill is not None
            assert character_skill.unlocked is True
            assert character_skill.level == 1
            assert character_skill.slot == 2

        used_slots = await get_used_skill_slots(character.id)

        assert used_slots == 2

        print("Skill 2 Slot=2")
        print("Used Slots=2/2")
        print("✅ Second slot works correctly.")

        # ============================================================
        # TEST 7 - Third skill blocked before Level 60
        # ============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 7 - THIRD SKILL BEFORE LEVEL 60")
        print("-" * 80)

        can_learn, message = await can_learn_skill(
            character.id,
            SKILL_3_ID,
        )

        print(f"Can Learn Skill 3={can_learn}")
        print(f"Message={message}")

        assert can_learn is False

        print("✅ Third skill correctly blocked at Level 20.")

        # ============================================================
        # TEST 8 - Level 60 unlocks third slot
        # ============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 8 - THIRD SLOT AT LEVEL 60")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == character.id
                )
            )

            assert character is not None

            character.level = 60

            await session.commit()

        max_slots = get_unlocked_skill_slots(60)

        assert max_slots == 3

        can_learn, message = await can_learn_skill(
            character.id,
            SKILL_3_ID,
        )

        print(f"Character Level=60")
        print(f"Max Slots={max_slots}")
        print(f"Can Learn Skill 3={can_learn}")
        print(f"Message={message}")

        assert can_learn is True

        success, message = await unlock_skill(
            character.telegram_id,
            SKILL_3_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is True

        async with AsyncSessionLocal() as session:
            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id,
                    CharacterSkill.skill_id == SKILL_3_ID,
                )
            )

            assert character_skill is not None
            assert character_skill.unlocked is True
            assert character_skill.level == 1
            assert character_skill.slot == 3

        used_slots = await get_used_skill_slots(character.id)

        assert used_slots == 3

        print("Skill 3 Slot=3")
        print("Used Slots=3/3")
        print("✅ Third slot works correctly.")

        # ============================================================
        # TEST 9 - Fourth skill blocked
        # ============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 9 - FOURTH SKILL BLOCK")
        print("-" * 80)

        can_learn, message = await can_learn_skill(
            character.id,
            SKILL_4_ID,
        )

        print(f"Can Learn Skill 4={can_learn}")
        print(f"Message={message}")

        assert can_learn is False

        success, message = await unlock_skill(
            character.telegram_id,
            SKILL_4_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is False

        used_slots = await get_used_skill_slots(character.id)

        assert used_slots == 3

        print("Used Slots=3/3")
        print("✅ Fourth skill correctly blocked.")

        # ============================================================
        # TEST 10 - Final DB state
        # ============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 10 - FINAL TEST STATE")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id,
                    CharacterSkill.skill_id.in_(
                        [
                            SKILL_1_ID,
                            SKILL_2_ID,
                            SKILL_3_ID,
                            SKILL_4_ID,
                        ]
                    ),
                )
            )

            character_skills = list(result.scalars().all())

            unlocked = [
                cs for cs in character_skills
                if cs.unlocked
            ]

            assert len(unlocked) == 3

            slots = sorted(
                cs.slot
                for cs in unlocked
                if cs.slot is not None
            )

            assert slots == [1, 2, 3]

        print("Unlocked Skills=3")
        print("Slots=[1, 2, 3]")
        print("✅ Final skill state is correct.")

    finally:
        # ============================================================
        # RESTORE DATABASE
        # ============================================================
        print("\n" + "=" * 80)
        print("🧹 RESTORING DATABASE")
        print("-" * 80)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.name == TEST_CHARACTER_NAME
                )
            )

            if character is not None:
                character.level = original_level

                for skill_id in (
                    SKILL_1_ID,
                    SKILL_2_ID,
                    SKILL_3_ID,
                    SKILL_4_ID,
                ):
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
    print("🎉 ALL SKILL LEARN FLOW TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())