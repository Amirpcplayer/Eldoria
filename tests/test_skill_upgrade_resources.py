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
    print("WORLD ELDORIA - SKILL UPGRADE RESOURCE TEST")
    print("=" * 80)

    # ========================================================
    # Load Character + Skill
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
        print(f"Level={character.level}")
        print(f"Character XP={character.xp}")
        print(f"Skill XP={character.skill_xp}")
        print(f"Gold={character.gold}")

        print("\n" + "=" * 80)
        print("🔮 SKILL")
        print("-" * 80)

        print(f"Name={skill.name}")
        print(f"Skill ID={skill.id}")
        print(f"Level={character_skill.level}")
        print(f"Max Level={skill.max_level}")

    # ========================================================
    # Upgrade Info
    # ========================================================

    success, message, info = await get_skill_upgrade_info(
        telegram_id,
        skill.id,
    )

    print("\n" + "=" * 80)
    print("📋 UPGRADE INFORMATION")
    print("-" * 80)

    print(f"Success={success}")
    print(f"Message={message}")

    if not success or info is None:
        print("❌ Could not get upgrade information.")
        return

    xp_cost = info["xp_cost"]
    gold_cost = info["gold_cost"]

    print(f"Current Level={info['current_level']}")
    print(f"Next Level={info['next_level']}")
    print(f"XP Cost={xp_cost}")
    print(f"Gold Cost={gold_cost}")

    # ========================================================
    # Prepare Temporary Resources
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 PREPARING TEST RESOURCES")
    print("-" * 80)

    temporary_skill_xp = max(
        original_skill_xp,
        xp_cost,
    )

    temporary_gold = max(
        original_gold,
        gold_cost,
    )

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        if character is None:
            print("❌ Character not found.")
            return

        character.skill_xp = temporary_skill_xp
        character.gold = temporary_gold

        await session.commit()

    print(f"Temporary Skill XP={temporary_skill_xp}")
    print(f"Temporary Gold={temporary_gold}")

    # ========================================================
    # Test 1 - Successful Upgrade
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 1 - SUCCESSFUL UPGRADE")
    print("-" * 80)

    before_level = original_level
    before_skill_xp = temporary_skill_xp
    before_gold = temporary_gold

    success, message = await upgrade_skill(
        telegram_id,
        skill.id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if not success:
        print("❌ Upgrade should have succeeded.")
        return

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
            print("❌ Failed to reload upgraded state.")
            return

        after_level = character_skill.level
        after_skill_xp = character.skill_xp
        after_gold = character.gold
        after_character_xp = character.xp

    print("\n" + "=" * 80)
    print("📊 UPGRADE RESULT")
    print("-" * 80)

    print(f"Level: {before_level} -> {after_level}")
    print(f"Skill XP: {before_skill_xp} -> {after_skill_xp}")
    print(f"Gold: {before_gold} -> {after_gold}")
    print(
        f"Character XP: "
        f"{original_character_xp} -> "
        f"{after_character_xp}"
    )

    # ========================================================
    # Assertions
    # ========================================================

    if after_level != before_level + 1:
        print("❌ Skill Level did not increase by exactly 1.")
        return

    if after_skill_xp != before_skill_xp - xp_cost:
        print("❌ Skill XP was consumed incorrectly.")
        return

    if after_gold != before_gold - gold_cost:
        print("❌ Gold was consumed incorrectly.")
        return

    if after_character_xp != original_character_xp:
        print("❌ Character XP changed unexpectedly.")
        return

    print("✅ Level +1")
    print("✅ Skill XP cost correct")
    print("✅ Gold cost correct")
    print("✅ Character XP unchanged")

    # ========================================================
    # Test 2 - Skill Power
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 2 - SKILL POWER GROWTH")
    print("-" * 80)

    old_power = get_skill_power(
        skill,
        before_level,
    )

    new_power = get_skill_power(
        skill,
        after_level,
    )

    print(f"Old Power={old_power}")
    print(f"New Power={new_power}")

    if new_power <= old_power:
        print("❌ Skill power did not increase.")
        return

    print("✅ Skill power increased.")

    # ========================================================
    # Test 3 - Insufficient Skill XP
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 3 - INSUFFICIENT SKILL XP")
    print("-" * 80)

    # برای Level فعلی، هزینه Upgrade بعدی را دوباره می‌گیریم.
    success, message, next_info = await get_skill_upgrade_info(
        telegram_id,
        skill.id,
    )

    if not success or next_info is None:
        print("❌ Could not get next upgrade information.")
        return

    next_xp_cost = next_info["xp_cost"]
    next_gold_cost = next_info["gold_cost"]

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        if character is None:
            print("❌ Character not found.")
            return

        # Skill XP کمتر از هزینه
        character.skill_xp = max(
            0,
            next_xp_cost - 1,
        )

        # Gold کافی
        character.gold = next_gold_cost

        await session.commit()

    success, message = await upgrade_skill(
        telegram_id,
        skill.id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if success:
        print("❌ Upgrade succeeded with insufficient Skill XP.")
        return

    if "Skill XP" not in message:
        print("❌ Upgrade was blocked for an unexpected reason.")
        return

    print("✅ Insufficient Skill XP correctly blocked.")

    # ========================================================
    # Test 4 - Insufficient Gold
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 4 - INSUFFICIENT GOLD")
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

        # Skill XP کاملاً کافی
        character.skill_xp = next_xp_cost

        # Gold دقیقاً یک واحد کمتر از هزینه
        character.gold = max(
            0,
            next_gold_cost - 1,
        )

        await session.commit()

    success, message = await upgrade_skill(
        telegram_id,
        skill.id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if success:
        print("❌ Upgrade succeeded with insufficient Gold.")
        return

    if "Gold" not in message:
        print("❌ Upgrade was blocked for an unexpected reason.")
        return

    print("✅ Insufficient Gold correctly blocked.")

    # ========================================================
    # Test 5 - Resource Integrity After Failed Upgrades
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 5 - FAILED UPGRADE RESOURCE INTEGRITY")
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

        failed_level = character_skill.level
        failed_skill_xp = character.skill_xp
        failed_gold = character.gold

    print(f"Level={failed_level}")
    print(f"Skill XP={failed_skill_xp}")
    print(f"Gold={failed_gold}")

    if failed_level != after_level:
        print("❌ Skill level changed during failed upgrade.")
        return

    if failed_skill_xp != next_xp_cost:
        print("❌ Skill XP changed during failed upgrade.")
        return

    if failed_gold != next_gold_cost - 1:
        print("❌ Gold changed during failed upgrade.")
        return

    print("✅ Skill level unchanged.")
    print("✅ Skill XP unchanged.")
    print("✅ Gold unchanged.")

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
    print("🎉 ALL SKILL UPGRADE RESOURCE TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())