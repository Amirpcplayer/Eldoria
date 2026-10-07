import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal

from models.character import Character
from models.character_skill import CharacterSkill
from models.skill import Skill

from services.skill_service import (
    get_skill_power,
    get_skill_upgrade_info,
    upgrade_skill,
)


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL MAX LEVEL TEST")
    print("=" * 80)

    # ========================================================
    # Load Character + Learned Skill
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

        result = await session.execute(
            select(
                CharacterSkill,
                Skill,
            )
            .join(
                Skill,
                Skill.id == CharacterSkill.skill_id,
            )
            .where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.unlocked.is_(True),
                Skill.is_active.is_(True),
            )
            .order_by(
                CharacterSkill.id
            )
        )

        row = result.first()

        if row is None:
            print("❌ No learned skill found.")
            return

        character_skill, skill = row

        # ====================================================
        # Save Original State
        # ====================================================

        original_level = character_skill.level
        original_skill_xp = character.skill_xp
        original_gold = character.gold
        original_character_xp = character.xp

        print("\n" + "=" * 80)
        print("👤 CHARACTER")
        print("-" * 80)

        print(f"Name={character.name}")
        print(f"Character Level={character.level}")
        print(f"Character XP={character.xp}")
        print(f"Skill XP={character.skill_xp}")
        print(f"Gold={character.gold}")

        print("\n" + "=" * 80)
        print("🔮 SKILL")
        print("-" * 80)

        print(f"Name={skill.name}")
        print(f"Skill ID={skill.id}")
        print(f"Current Level={character_skill.level}")
        print(f"Max Level={skill.max_level}")

    # ========================================================
    # Validate Max Level
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 1 - MAX LEVEL CONFIGURATION")
    print("-" * 80)

    max_level = skill.max_level

    print(f"Configured Max Level={max_level}")

    if max_level != 10:
        print(
            f"❌ Expected Max Level=10, "
            f"but found {max_level}."
        )
        return

    print("✅ Max Level is correctly configured as 10.")

    # ========================================================
    # Temporarily Set Skill To Max Level
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 2 - SET SKILL TO MAX LEVEL")
    print("-" * 80)

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill.id,
            )
        )

        if character is None or character_skill is None:
            print("❌ Character or skill not found.")
            return

        character_skill.level = max_level

        # منابع زیاد برای اطمینان از اینکه
        # فقط Max Level مانع Upgrade می‌شود.
        character.skill_xp = 999999
        character.gold = 999999

        await session.commit()

    print(f"Temporary Skill Level={max_level}")
    print("Temporary Skill XP=999999")
    print("Temporary Gold=999999")
    print("✅ Skill placed at Max Level.")

    # ========================================================
    # Test 3 - Upgrade Info At Max Level
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 3 - UPGRADE INFO AT MAX LEVEL")
    print("-" * 80)

    success, message, info = await get_skill_upgrade_info(
        telegram_id,
        skill.id,
    )

    print(f"Success={success}")
    print(f"Message={message}")
    print(f"Info={info}")

    if success:
        print("❌ Upgrade info should fail at Max Level.")
        return

    if info is not None:
        print("❌ Upgrade info returned data at Max Level.")
        return

    if "حداکثر" not in message:
        print(
            "❌ Max Level message was not returned."
        )
        return

    print("✅ Upgrade info correctly blocked.")

    # ========================================================
    # Test 4 - Direct Upgrade At Max Level
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 4 - DIRECT UPGRADE AT MAX LEVEL")
    print("-" * 80)

    before_skill_xp = 999999
    before_gold = 999999
    before_level = max_level

    success, message = await upgrade_skill(
        telegram_id,
        skill.id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if success:
        print("❌ Upgrade succeeded beyond Max Level.")
        return

    print("✅ Direct upgrade correctly blocked.")

    # ========================================================
    # Reload State
    # ========================================================

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill.id,
            )
        )

        if character is None or character_skill is None:
            print("❌ Failed to reload state.")
            return

        after_level = character_skill.level
        after_skill_xp = character.skill_xp
        after_gold = character.gold

    print("\n" + "=" * 80)
    print("📊 MAX LEVEL RESULT")
    print("-" * 80)

    print(f"Level: {before_level} -> {after_level}")
    print(f"Skill XP: {before_skill_xp} -> {after_skill_xp}")
    print(f"Gold: {before_gold} -> {after_gold}")

    if after_level != max_level:
        print("❌ Skill level changed at Max Level.")
        return

    if after_skill_xp != before_skill_xp:
        print("❌ Skill XP changed at Max Level.")
        return

    if after_gold != before_gold:
        print("❌ Gold changed at Max Level.")
        return

    print("✅ Skill Level unchanged.")
    print("✅ Skill XP unchanged.")
    print("✅ Gold unchanged.")

    # ========================================================
    # Test 5 - Skill Power At Max Level
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 5 - MAX LEVEL SKILL POWER")
    print("-" * 80)

    max_power = get_skill_power(
        skill,
        max_level,
    )

    next_power = get_skill_power(
        skill,
        max_level + 1,
    )

    print(f"Max Level Power={max_power}")
    print(f"Hypothetical Level 11 Power={next_power}")

    if max_power <= 0:
        print("❌ Max Level Skill Power is invalid.")
        return

    print("✅ Max Level Skill Power is valid.")
    print(
        "ℹ️ Level 11 power is shown only for calculation "
        "and must NOT be reachable through upgrade."
    )

    # ========================================================
    # Restore Original State
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

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill.id,
            )
        )

        if character is None or character_skill is None:
            print("❌ Could not restore state.")
            return

        character.skill_xp = original_skill_xp
        character.gold = original_gold
        character.xp = original_character_xp

        character_skill.level = original_level

        await session.commit()

    # ========================================================
    # Verify Restore
    # ========================================================

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill.id,
            )
        )

        if character is None or character_skill is None:
            print("❌ Restore verification failed.")
            return

        if character.skill_xp != original_skill_xp:
            print("❌ Skill XP was not restored.")
            return

        if character.gold != original_gold:
            print("❌ Gold was not restored.")
            return

        if character.xp != original_character_xp:
            print("❌ Character XP was not restored.")
            return

        if character_skill.level != original_level:
            print("❌ Skill level was not restored.")
            return

    print("✅ Skill XP restored.")
    print("✅ Gold restored.")
    print("✅ Character XP restored.")
    print("✅ Skill level restored.")

    # ========================================================
    # Final
    # ========================================================

    print("\n" + "=" * 80)
    print("🎉 ALL SKILL MAX LEVEL TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())