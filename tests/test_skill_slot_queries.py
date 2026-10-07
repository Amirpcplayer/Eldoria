import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import asyncio

from sqlalchemy import delete, select

from database.database import AsyncSessionLocal

from models.character import Character
from models.character_skill import CharacterSkill
from models.skill import Skill

from services.skill_service import (
    can_learn_skill,
    get_max_skill_slots,
    get_next_available_slot,
    get_unlocked_skill_slots,
    get_used_skill_slots,
    unlock_skill,
)


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL SLOT QUERY TEST")
    print("=" * 80)

    # ========================================================
    # LOAD CHARACTER
    # ========================================================

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character)
            .order_by(Character.id)
            .limit(1)
        )

        if character is None:
            print("❌ No character found.")
            return

        character_id = character.id
        telegram_id = character.telegram_id

        skills_result = await session.execute(
            select(Skill)
            .where(Skill.is_active.is_(True))
            .order_by(Skill.id)
        )

        skills = list(skills_result.scalars().all())

        if len(skills) < 4:
            print("❌ At least 4 active skills are required.")
            return

        character_skills_result = await session.execute(
            select(CharacterSkill)
            .where(
                CharacterSkill.character_id == character_id
            )
            .order_by(CharacterSkill.id)
        )

        original_character_skills = list(
            character_skills_result.scalars().all()
        )

        original_character_level = character.level
        original_character_xp = character.xp
        original_skill_xp = character.skill_xp
        original_gold = character.gold

        original_skill_states = {
            cs.skill_id: {
                "level": cs.level,
                "unlocked": cs.unlocked,
                "slot": cs.slot,
            }
            for cs in original_character_skills
        }

    print("\n" + "=" * 80)
    print("👤 CHARACTER")
    print("-" * 80)

    print(f"Name={character.name}")
    print(f"Character ID={character_id}")
    print(f"Telegram ID={telegram_id}")
    print(f"Original Level={character.level}")

    # ========================================================
    # TEST 1 - SLOT CONFIGURATION
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 1 - SLOT CONFIGURATION")
    print("-" * 80)

    expected = {
        1: 1,
        19: 1,
        20: 2,
        59: 2,
        60: 3,
        100: 3,
    }

    for level, expected_slots in expected.items():

        unlocked_slots = get_unlocked_skill_slots(level)
        max_slots = get_max_skill_slots(level)

        print(
            f"Level={level} | "
            f"Unlocked={unlocked_slots} | "
            f"Max={max_slots}"
        )

        if unlocked_slots != expected_slots:
            print("❌ get_unlocked_skill_slots failed.")
            return

        if max_slots != expected_slots:
            print("❌ get_max_skill_slots failed.")
            return

    print("✅ Slot configuration is correct.")

    # ========================================================
    # TEMPORARY CLEAN STATE
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 PREPARING TEMPORARY STATE")
    print("-" * 80)

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        if character is None:
            print("❌ Character not found.")
            return

        await session.execute(
            delete(CharacterSkill).where(
                CharacterSkill.character_id == character_id
            )
        )

        character.level = 60
        character.skill_xp = 999999
        character.gold = 999999

        await session.commit()

    print("Temporary Level=60")
    print("Temporary Slots=3")
    print("Temporary Used Skills=0")

    # ========================================================
    # TEST 2 - EMPTY SLOT QUERIES
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 2 - EMPTY SLOT QUERIES")
    print("-" * 80)

    used_slots = await get_used_skill_slots(
        character_id
    )

    next_slot = await get_next_available_slot(
        character_id,
        60,
    )

    print(f"Used Slots={used_slots}")
    print(f"Next Available Slot={next_slot}")

    if used_slots != 0:
        print("❌ Expected 0 used slots.")
        return

    if next_slot != 1:
        print("❌ Expected next available slot to be 1.")
        return

    print("✅ Empty slot queries are correct.")

    # ========================================================
    # TEST 3 - CAN LEARN FIRST SKILL
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 3 - CAN LEARN FIRST SKILL")
    print("-" * 80)

    skill_1 = skills[0]

    can_learn, message = await can_learn_skill(
        character_id,
        skill_1.id,
    )

    print(f"Skill={skill_1.name}")
    print(f"Unlock Level={skill_1.unlock_level}")
    print(f"Can Learn={can_learn}")
    print(f"Message={message}")

    if not can_learn:
        print("❌ First skill should be learnable.")
        return

    print("✅ First skill can be learned.")

    # ========================================================
    # TEST 4 - UNLOCK FIRST SKILL
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 4 - UNLOCK FIRST SKILL")
    print("-" * 80)

    success, message = await unlock_skill(
        telegram_id,
        skill_1.id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if not success:
        print("❌ First skill unlock failed.")
        return

    used_slots = await get_used_skill_slots(
        character_id
    )

    next_slot = await get_next_available_slot(
        character_id,
        60,
    )

    print(f"Used Slots={used_slots}")
    print(f"Next Available Slot={next_slot}")

    if used_slots != 1:
        print("❌ Expected 1 used slot.")
        return

    if next_slot != 2:
        print("❌ Expected next available slot to be 2.")
        return

    print("✅ Slot queries updated correctly.")

    # ========================================================
    # TEST 5 - SECOND SKILL
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 5 - SECOND SKILL")
    print("-" * 80)

    skill_2 = skills[1]

    can_learn, message = await can_learn_skill(
        character_id,
        skill_2.id,
    )

    print(f"Skill={skill_2.name}")
    print(f"Can Learn={can_learn}")
    print(f"Message={message}")

    if not can_learn:
        print("❌ Second skill should be learnable.")
        return

    success, message = await unlock_skill(
        telegram_id,
        skill_2.id,
    )

    print(f"Unlock Success={success}")
    print(f"Message={message}")

    if not success:
        print("❌ Second skill unlock failed.")
        return

    used_slots = await get_used_skill_slots(
        character_id
    )

    next_slot = await get_next_available_slot(
        character_id,
        60,
    )

    print(f"Used Slots={used_slots}")
    print(f"Next Available Slot={next_slot}")

    if used_slots != 2:
        print("❌ Expected 2 used slots.")
        return

    if next_slot != 3:
        print("❌ Expected next available slot to be 3.")
        return

    print("✅ Second slot state is correct.")

    # ========================================================
    # TEST 6 - THIRD SKILL
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 6 - THIRD SKILL")
    print("-" * 80)

    skill_3 = skills[2]

    can_learn, message = await can_learn_skill(
        character_id,
        skill_3.id,
    )

    print(f"Skill={skill_3.name}")
    print(f"Can Learn={can_learn}")
    print(f"Message={message}")

    if not can_learn:
        print("❌ Third skill should be learnable.")
        return

    success, message = await unlock_skill(
        telegram_id,
        skill_3.id,
    )

    print(f"Unlock Success={success}")
    print(f"Message={message}")

    if not success:
        print("❌ Third skill unlock failed.")
        return

    used_slots = await get_used_skill_slots(
        character_id
    )

    next_slot = await get_next_available_slot(
        character_id,
        60,
    )

    print(f"Used Slots={used_slots}")
    print(f"Next Available Slot={next_slot}")

    if used_slots != 3:
        print("❌ Expected 3 used slots.")
        return

    if next_slot is not None:
        print(
            f"❌ Expected no available slot, got {next_slot}."
        )
        return

    print("✅ All 3 slots are correctly occupied.")

    # ========================================================
    # TEST 7 - FOURTH SKILL BLOCKED
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 7 - FOURTH SKILL SLOT BLOCK")
    print("-" * 80)

    skill_4 = skills[3]

    can_learn, message = await can_learn_skill(
        character_id,
        skill_4.id,
    )

    print(f"Skill={skill_4.name}")
    print(f"Can Learn={can_learn}")
    print(f"Message={message}")

    if can_learn:
        print("❌ Fourth skill should be blocked.")
        return

    success, message = await unlock_skill(
        telegram_id,
        skill_4.id,
    )

    print(f"Unlock Success={success}")
    print(f"Message={message}")

    if success:
        print("❌ Fourth skill was incorrectly unlocked.")
        return

    print("✅ Fourth skill correctly blocked.")

    # ========================================================
    # TEST 8 - REACTIVATE LOCKED CharacterSkill
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 8 - REACTIVATE LOCKED CHARACTER SKILL")
    print("-" * 80)

    async with AsyncSessionLocal() as session:

        existing = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill_4.id,
            )
        )

        if existing is None:

            existing = CharacterSkill(
                character_id=character_id,
                skill_id=skill_4.id,
                level=7,
                slot=None,
                unlocked=False,
            )

            session.add(existing)

        else:

            existing.level = 7
            existing.slot = None
            existing.unlocked = False

        await session.commit()

    used_before = await get_used_skill_slots(
        character_id
    )

    next_before = await get_next_available_slot(
        character_id,
        60,
    )

    print(f"Used Slots Before Reactivate={used_before}")
    print(f"Next Slot Before Reactivate={next_before}")

    if used_before != 3:
        print(
            "❌ Locked CharacterSkill should not count as used."
        )
        return

    if next_before is not None:
        print(
            "❌ No slot should be available before reactivation."
        )
        return

    success, message = await unlock_skill(
        telegram_id,
        skill_4.id,
    )

    print(f"Reactivate Success={success}")
    print(f"Message={message}")

    if success:
        print(
            "❌ Reactivation should fail because "
            "all 3 slots are occupied."
        )
        return

    print(
        "✅ Reactivation correctly blocked by full slots."
    )

    # ========================================================
    # TEST 9 - FREE SLOT + REACTIVATE
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 9 - FREE SLOT + REACTIVATE")
    print("-" * 80)

    async with AsyncSessionLocal() as session:

        first = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill_1.id,
            )
        )

        if first is None:
            print("❌ First skill not found.")
            return

        first.unlocked = False
        first.slot = None

        await session.commit()

    used_after_remove = await get_used_skill_slots(
        character_id
    )

    next_after_remove = await get_next_available_slot(
        character_id,
        60,
    )

    print(f"Used Slots After Freeing Slot={used_after_remove}")
    print(f"Next Available Slot={next_after_remove}")

    if used_after_remove != 2:
        print("❌ Expected 2 used slots.")
        return

    if next_after_remove != 1:
        print(
            "❌ Expected Slot 1 to become available."
        )
        return

    success, message = await unlock_skill(
        telegram_id,
        skill_4.id,
    )

    print(f"Reactivate Success={success}")
    print(f"Message={message}")

    if not success:
        print("❌ Reactivation failed.")
        return

    async with AsyncSessionLocal() as session:

        reactivated = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill_4.id,
            )
        )

        if reactivated is None:
            print("❌ Reactivated skill not found.")
            return

        print(f"Level After Reactivate={reactivated.level}")
        print(f"Slot After Reactivate={reactivated.slot}")
        print(f"Unlocked={reactivated.unlocked}")

        if reactivated.level != 1:
            print(
                "❌ Reactivated skill should reset to Level 1."
            )
            return

        if reactivated.slot != 1:
            print(
                "❌ Reactivated skill should receive Slot 1."
            )
            return

        if not reactivated.unlocked:
            print(
                "❌ Reactivated skill should be unlocked."
            )
            return

    print("✅ Reactivation works correctly.")

    # ========================================================
    # RESTORE
    # ========================================================

    print("\n" + "=" * 80)
    print("♻️ RESTORING ORIGINAL STATE")
    print("-" * 80)

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        if character is None:
            print("❌ Character missing during restore.")
            return

        await session.execute(
            delete(CharacterSkill).where(
                CharacterSkill.character_id == character_id
            )
        )

        character.level = original_character_level
        character.xp = original_character_xp
        character.skill_xp = original_skill_xp
        character.gold = original_gold

        for skill_id, state in original_skill_states.items():

            session.add(
                CharacterSkill(
                    character_id=character_id,
                    skill_id=skill_id,
                    level=state["level"],
                    unlocked=state["unlocked"],
                    slot=state["slot"],
                )
            )

        await session.commit()

    # ========================================================
    # VERIFY RESTORE
    # ========================================================

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        restored_result = await session.execute(
            select(CharacterSkill)
            .where(
                CharacterSkill.character_id == character_id
            )
        )

        restored = list(
            restored_result.scalars().all()
        )

        if character is None:
            print("❌ Character restore failed.")
            return

        if character.level != original_character_level:
            print("❌ Character level restore failed.")
            return

        if character.xp != original_character_xp:
            print("❌ Character XP restore failed.")
            return

        if character.skill_xp != original_skill_xp:
            print("❌ Skill XP restore failed.")
            return

        if character.gold != original_gold:
            print("❌ Gold restore failed.")
            return

        if len(restored) != len(original_skill_states):
            print("❌ CharacterSkill restore count failed.")
            return

    print("✅ Character restored.")
    print("✅ Character XP restored.")
    print("✅ Skill XP restored.")
    print("✅ Gold restored.")
    print("✅ CharacterSkill records restored.")

    print("\n" + "=" * 80)
    print("🎉 ALL SKILL SLOT QUERY TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())