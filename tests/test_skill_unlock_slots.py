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
    get_unlocked_skill_slots,
    get_character_skills,
    get_unlocked_character_skills,
    is_skill_unlocked_by_level,
    unlock_skill,
)


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL UNLOCK & SLOT SYSTEM TEST")
    print("=" * 80)

    # ========================================================
    # LOAD CHARACTER + SKILLS
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

        if not skills:
            print("❌ No active skills found.")
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
        original_skill_xp = character.skill_xp
        original_gold = character.gold
        original_character_xp = character.xp

        original_skill_states = {
            cs.skill_id: {
                "level": cs.level,
                "unlocked": cs.unlocked,
                "slot": cs.slot,
            }
            for cs in original_character_skills
        }

    # ========================================================
    # CHARACTER
    # ========================================================

    print("\n" + "=" * 80)
    print("👤 CHARACTER")
    print("-" * 80)

    print(f"Name={character.name}")
    print(f"Character ID={character_id}")
    print(f"Character Level={character.level}")

    # ========================================================
    # ACTIVE SKILLS
    # ========================================================

    print("\n" + "=" * 80)
    print("🔮 ACTIVE SKILLS")
    print("-" * 80)

    for skill in skills:
        print(
            f"ID={skill.id} | "
            f"Name={skill.name} | "
            f"Unlock Level={skill.unlock_level} | "
            f"Max Level={skill.max_level}"
        )

    # ========================================================
    # TEST 1 - SLOT RULES
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 1 - SKILL SLOT RULES")
    print("-" * 80)

    expected_slots = [
        (1, 1),
        (19, 1),
        (20, 2),
        (59, 2),
        (60, 3),
        (100, 3),
    ]

    for level, expected in expected_slots:

        actual = get_unlocked_skill_slots(level)

        print(
            f"Character Level={level} | "
            f"Expected Slots={expected} | "
            f"Actual Slots={actual}"
        )

        if actual != expected:
            print(
                f"❌ Slot rule failed at Level {level}."
            )
            return

    print("✅ All skill slot rules are correct.")

    # ========================================================
    # TEST 2 - UNLOCK LEVEL LOGIC
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 2 - UNLOCK LEVEL CHECK")
    print("-" * 80)

    for skill in skills:

        unlock_level = skill.unlock_level

        below_level = max(1, unlock_level - 1)

        blocked = is_skill_unlocked_by_level(
            below_level,
            skill,
        )

        allowed = is_skill_unlocked_by_level(
            unlock_level,
            skill,
        )

        print(
            f"{skill.name} | "
            f"Unlock Level={unlock_level} | "
            f"Below={below_level}:{blocked} | "
            f"AtLevel={unlock_level}:{allowed}"
        )

        if unlock_level > 1 and blocked:
            print(
                f"❌ Skill {skill.id} can be unlocked "
                f"before its required level."
            )
            return

        if not allowed:
            print(
                f"❌ Skill {skill.id} cannot be unlocked "
                f"at its required level."
            )
            return

    print("✅ Unlock level logic is correct.")

    # ========================================================
    # TEST 3 - PREPARE TEMPORARY STATE
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 3 - PREPARE TEMPORARY STATE")
    print("-" * 80)

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        if character is None:
            print("❌ Character disappeared.")
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

    print("Temporary Character Level=60")
    print("Temporary Skill XP=999999")
    print("Temporary Gold=999999")
    print("Temporary learned skills=0")
    print("✅ Temporary state prepared.")

    # ========================================================
    # REQUIRE 3 SKILLS
    # ========================================================

    if len(skills) < 3:
        print(
            "❌ At least 3 active skills are required "
            "to test all 3 slots."
        )
        return

    test_skills = skills[:3]

    # ========================================================
    # TEST 4 - FIRST SKILL
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 4 - FIRST SKILL UNLOCK")
    print("-" * 80)

    first_skill = test_skills[0]

    success, message = await unlock_skill(
        telegram_id,
        first_skill.id,
    )

    print(f"Skill={first_skill.name}")
    print(f"Success={success}")
    print(f"Message={message}")

    if not success:
        print("❌ First skill unlock failed.")
        return

    async with AsyncSessionLocal() as session:

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == first_skill.id,
            )
        )

        if character_skill is None:
            print("❌ CharacterSkill was not created.")
            return

        print(f"Assigned Slot={character_skill.slot}")
        print(f"Level={character_skill.level}")
        print(f"Unlocked={character_skill.unlocked}")

        if character_skill.slot != 1:
            print("❌ First skill was not assigned to Slot 1.")
            return

        if character_skill.level != 1:
            print(
                "❌ Newly unlocked skill does not start at Level 1."
            )
            return

        if not character_skill.unlocked:
            print(
                "❌ Newly unlocked skill is not marked unlocked."
            )
            return

    print("✅ First skill unlocked correctly.")

    # ========================================================
    # TEST 5 - DUPLICATE
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 5 - DUPLICATE SKILL UNLOCK")
    print("-" * 80)

    success, message = await unlock_skill(
        telegram_id,
        first_skill.id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if success:
        print("❌ Duplicate skill unlock was allowed.")
        return

    print("✅ Duplicate skill unlock correctly blocked.")

    # ========================================================
    # TEST 6 - SECOND SLOT
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 6 - SECOND SKILL SLOT")
    print("-" * 80)

    second_skill = test_skills[1]

    success, message = await unlock_skill(
        telegram_id,
        second_skill.id,
    )

    print(f"Skill={second_skill.name}")
    print(f"Success={success}")
    print(f"Message={message}")

    if not success:
        print("❌ Second skill unlock failed.")
        return

    async with AsyncSessionLocal() as session:

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == second_skill.id,
            )
        )

        if character_skill is None:
            print(
                "❌ Second CharacterSkill was not created."
            )
            return

        print(f"Assigned Slot={character_skill.slot}")

        if character_skill.slot != 2:
            print(
                "❌ Second skill was not assigned to Slot 2."
            )
            return

    print("✅ Second skill correctly assigned to Slot 2.")

    # ========================================================
    # TEST 7 - THIRD SLOT
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 7 - THIRD SKILL SLOT")
    print("-" * 80)

    third_skill = test_skills[2]

    success, message = await unlock_skill(
        telegram_id,
        third_skill.id,
    )

    print(f"Skill={third_skill.name}")
    print(f"Success={success}")
    print(f"Message={message}")

    if not success:
        print("❌ Third skill unlock failed.")
        return

    async with AsyncSessionLocal() as session:

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == third_skill.id,
            )
        )

        if character_skill is None:
            print(
                "❌ Third CharacterSkill was not created."
            )
            return

        print(f"Assigned Slot={character_skill.slot}")

        if character_skill.slot != 3:
            print(
                "❌ Third skill was not assigned to Slot 3."
            )
            return

    print("✅ Third skill correctly assigned to Slot 3.")

    # ========================================================
    # TEST 8 - FOURTH SLOT
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 8 - SLOT LIMIT")
    print("-" * 80)

    if len(skills) < 4:

        print(
            "ℹ️ Less than 4 active skills exist; "
            "skipping fourth-slot test."
        )

    else:

        fourth_skill = skills[3]

        success, message = await unlock_skill(
            telegram_id,
            fourth_skill.id,
        )

        print(f"Skill={fourth_skill.name}")
        print(f"Success={success}")
        print(f"Message={message}")

        if success:
            print(
                "❌ Fourth skill was unlocked "
                "despite only 3 slots."
            )
            return

        print(
            "✅ Fourth skill correctly blocked by slot limit."
        )

    # ========================================================
    # TEST 9 - UNLOCKED SKILL COUNT
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 9 - UNLOCKED SKILL COUNT")
    print("-" * 80)

    unlocked_skills = await get_unlocked_character_skills(
        character_id
    )

    print(
        f"Unlocked Skill Count={len(unlocked_skills)}"
    )

    if len(unlocked_skills) != 3:
        print(
            "❌ Expected exactly 3 unlocked skills."
        )
        return

    print("✅ Exactly 3 skills are unlocked.")

    # ========================================================
    # TEST 10 - CHARACTER SKILL LIST
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 10 - CHARACTER SKILL LIST")
    print("-" * 80)

    character_skills = await get_character_skills(
        character_id
    )

    print(
        f"Character Skill Count={len(character_skills)}"
    )

    if len(character_skills) != 3:
        print(
            "❌ Character skill list does not contain "
            "exactly 3 skills."
        )
        return

    slots = []

    for skill_obj, character_skill in character_skills:

        print(
            f"{skill_obj.name} | "
            f"Level={character_skill.level} | "
            f"Slot={character_skill.slot} | "
            f"Unlocked={character_skill.unlocked}"
        )

        slots.append(character_skill.slot)

    if sorted(slots) != [1, 2, 3]:
        print(
            f"❌ Expected slots [1, 2, 3], "
            f"got {sorted(slots)}"
        )
        return

    print(
        "✅ Character skill list and slots are correct."
    )

    # ========================================================
    # RESTORE ORIGINAL STATE
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
            print(
                "❌ Character not found during restore."
            )
            return

        await session.execute(
            delete(CharacterSkill).where(
                CharacterSkill.character_id == character_id
            )
        )

        character.level = original_character_level
        character.skill_xp = original_skill_xp
        character.gold = original_gold
        character.xp = original_character_xp

        for skill_id, state in original_skill_states.items():

            restored = CharacterSkill(
                character_id=character_id,
                skill_id=skill_id,
                level=state["level"],
                unlocked=state["unlocked"],
                slot=state["slot"],
            )

            session.add(restored)

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
            .order_by(CharacterSkill.id)
        )

        restored_skills = list(
            restored_result.scalars().all()
        )

        if character is None:
            print(
                "❌ Restore verification failed."
            )
            return

        if character.level != original_character_level:
            print(
                "❌ Character level restore failed."
            )
            return

        if character.skill_xp != original_skill_xp:
            print(
                "❌ Skill XP restore failed."
            )
            return

        if character.gold != original_gold:
            print(
                "❌ Gold restore failed."
            )
            return

        if character.xp != original_character_xp:
            print(
                "❌ Character XP restore failed."
            )
            return

        if len(restored_skills) != len(original_skill_states):
            print(
                "❌ CharacterSkill count restore failed."
            )
            return

        restored_by_skill_id = {
            cs.skill_id: cs
            for cs in restored_skills
        }

        for skill_id, original in original_skill_states.items():

            restored = restored_by_skill_id.get(skill_id)

            if restored is None:
                print(
                    f"❌ Skill {skill_id} "
                    f"was not restored."
                )
                return

            if restored.level != original["level"]:
                print(
                    f"❌ Skill {skill_id} "
                    f"level restore failed."
                )
                return

            if restored.unlocked != original["unlocked"]:
                print(
                    f"❌ Skill {skill_id} "
                    f"unlock state restore failed."
                )
                return

            if restored.slot != original["slot"]:
                print(
                    f"❌ Skill {skill_id} "
                    f"slot restore failed."
                )
                return

    print("✅ Character level restored.")
    print("✅ Character XP restored.")
    print("✅ Skill XP restored.")
    print("✅ Gold restored.")
    print("✅ CharacterSkill records restored.")
    print("✅ Skill levels restored.")
    print("✅ Unlock states restored.")
    print("✅ Skill slots restored.")

    # ========================================================
    # FINAL
    # ========================================================

    print("\n" + "=" * 80)
    print("🎉 ALL SKILL UNLOCK & SLOT TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())