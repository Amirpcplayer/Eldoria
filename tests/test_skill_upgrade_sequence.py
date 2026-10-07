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
    SKILL_UPGRADE_COSTS,
    get_skill_power,
    get_skill_upgrade_info,
    upgrade_skill,
)


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL UPGRADE SEQUENCE TEST")
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
            .order_by(CharacterSkill.id)
        )

        row = result.first()

        if row is None:
            print("❌ No learned skill found.")
            return

        character_skill, skill = row

        # ====================================================
        # Save Original State
        # ====================================================

        original_skill_level = character_skill.level
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
    # Validate Configuration
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 1 - UPGRADE COST TABLE")
    print("-" * 80)

    expected_levels = list(range(1, skill.max_level))

    for level in expected_levels:
        cost = SKILL_UPGRADE_COSTS.get(level)

        if cost is None:
            print(
                f"❌ Missing upgrade cost for "
                f"Level {level} -> {level + 1}"
            )
            return

        print(
            f"Lv.{level} -> Lv.{level + 1} | "
            f"XP={cost['xp']} | "
            f"Gold={cost['gold']}"
        )

    print("✅ All upgrade levels have configured costs.")

    # ========================================================
    # Prepare Temporary State
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 2 - PREPARE TEMPORARY STATE")
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

        character_skill.level = 1

        # منابع کافی برای تمام ارتقاها
        character.skill_xp = 999999
        character.gold = 999999

        await session.commit()

    print("Temporary Skill Level=1")
    print("Temporary Skill XP=999999")
    print("Temporary Gold=999999")
    print("✅ Temporary state prepared.")

    # ========================================================
    # Sequential Upgrade Test
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 3 - SEQUENTIAL UPGRADE LEVEL 1 -> MAX")
    print("-" * 80)

    total_xp_cost = 0
    total_gold_cost = 0

    previous_power = None

    for expected_level in range(1, skill.max_level):

        expected_next_level = expected_level + 1

        cost = SKILL_UPGRADE_COSTS.get(expected_level)

        if cost is None:
            print(
                f"❌ Missing cost for "
                f"Lv.{expected_level} -> Lv.{expected_next_level}"
            )
            return

        # ----------------------------------------------------
        # Upgrade Info
        # ----------------------------------------------------

        success, message, info = await get_skill_upgrade_info(
            telegram_id,
            skill.id,
        )

        if not success:
            print(
                f"❌ Upgrade info failed at "
                f"Lv.{expected_level}."
            )
            print(f"Message={message}")
            return

        if info is None:
            print(
                f"❌ Upgrade info returned None at "
                f"Lv.{expected_level}."
            )
            return

        if info["current_level"] != expected_level:
            print(
                f"❌ Current level mismatch. "
                f"Expected={expected_level}, "
                f"Got={info['current_level']}"
            )
            return

        if info["next_level"] != expected_next_level:
            print(
                f"❌ Next level mismatch. "
                f"Expected={expected_next_level}, "
                f"Got={info['next_level']}"
            )
            return

        if info["xp_cost"] != cost["xp"]:
            print(
                f"❌ XP cost mismatch at "
                f"Lv.{expected_level}. "
                f"Expected={cost['xp']}, "
                f"Got={info['xp_cost']}"
            )
            return

        if info["gold_cost"] != cost["gold"]:
            print(
                f"❌ Gold cost mismatch at "
                f"Lv.{expected_level}. "
                f"Expected={cost['gold']}, "
                f"Got={info['gold_cost']}"
            )
            return

        current_power = info["current_power"]
        next_power = info["next_power"]

        if next_power <= current_power:
            print(
                f"❌ Skill Power did not increase: "
                f"{current_power} -> {next_power}"
            )
            return

        if previous_power is not None and current_power != previous_power:
            print(
                f"❌ Power continuity mismatch. "
                f"Previous={previous_power}, "
                f"Current={current_power}"
            )
            return

        # ----------------------------------------------------
        # Execute Upgrade
        # ----------------------------------------------------

        success, message = await upgrade_skill(
            telegram_id,
            skill.id,
        )

        if not success:
            print(
                f"❌ Upgrade failed at "
                f"Lv.{expected_level} -> "
                f"Lv.{expected_next_level}"
            )
            print(f"Message={message}")
            return

        # ----------------------------------------------------
        # Verify Database State
        # ----------------------------------------------------

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

            actual_level = character_skill.level
            actual_skill_xp = character.skill_xp
            actual_gold = character.gold
            actual_character_xp = character.xp

        expected_skill_xp = 999999 - (
            total_xp_cost + cost["xp"]
        )

        expected_gold = 999999 - (
            total_gold_cost + cost["gold"]
        )

        if actual_level != expected_next_level:
            print(
                f"❌ Level mismatch after upgrade. "
                f"Expected={expected_next_level}, "
                f"Got={actual_level}"
            )
            return

        if actual_skill_xp != expected_skill_xp:
            print(
                f"❌ Skill XP mismatch. "
                f"Expected={expected_skill_xp}, "
                f"Got={actual_skill_xp}"
            )
            return

        if actual_gold != expected_gold:
            print(
                f"❌ Gold mismatch. "
                f"Expected={expected_gold}, "
                f"Got={actual_gold}"
            )
            return

        if actual_character_xp != original_character_xp:
            print(
                f"❌ Character XP changed unexpectedly. "
                f"Expected={original_character_xp}, "
                f"Got={actual_character_xp}"
            )
            return

        # ----------------------------------------------------
        # Verify Power
        # ----------------------------------------------------

        actual_power = get_skill_power(
            skill,
            actual_level,
        )

        if actual_power != next_power:
            print(
                f"❌ Skill Power mismatch. "
                f"Expected={next_power}, "
                f"Got={actual_power}"
            )
            return

        print(
            f"Lv.{expected_level} -> Lv.{expected_next_level} | "
            f"XP -{cost['xp']} | "
            f"Gold -{cost['gold']} | "
            f"Power {current_power}->{next_power} | "
            f"✅"
        )

        total_xp_cost += cost["xp"]
        total_gold_cost += cost["gold"]
        previous_power = next_power

    # ========================================================
    # Final Max Level Verification
    # ========================================================

    print("\n" + "=" * 80)
    print("🧪 TEST 4 - FINAL MAX LEVEL")
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
            print("❌ Failed to load final state.")
            return

        final_level = character_skill.level
        final_skill_xp = character.skill_xp
        final_gold = character.gold

    expected_final_skill_xp = 999999 - total_xp_cost
    expected_final_gold = 999999 - total_gold_cost

    print(f"Final Skill Level={final_level}")
    print(f"Expected Skill Level={skill.max_level}")

    print(f"Final Skill XP={final_skill_xp}")
    print(f"Expected Skill XP={expected_final_skill_xp}")

    print(f"Final Gold={final_gold}")
    print(f"Expected Gold={expected_final_gold}")

    print(f"Total XP Cost={total_xp_cost}")
    print(f"Total Gold Cost={total_gold_cost}")

    if final_level != skill.max_level:
        print("❌ Final level is not Max Level.")
        return

    if final_skill_xp != expected_final_skill_xp:
        print("❌ Final Skill XP is incorrect.")
        return

    if final_gold != expected_final_gold:
        print("❌ Final Gold is incorrect.")
        return

    print("✅ Final Max Level is correct.")
    print("✅ Total Skill XP cost is correct.")
    print("✅ Total Gold cost is correct.")

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
            print("❌ Could not restore original state.")
            return

        character_skill.level = original_skill_level
        character.skill_xp = original_skill_xp
        character.gold = original_gold
        character.xp = original_character_xp

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

        if character_skill.level != original_skill_level:
            print("❌ Skill level restore failed.")
            return

        if character.skill_xp != original_skill_xp:
            print("❌ Skill XP restore failed.")
            return

        if character.gold != original_gold:
            print("❌ Gold restore failed.")
            return

        if character.xp != original_character_xp:
            print("❌ Character XP restore failed.")
            return

    print("✅ Skill level restored.")
    print("✅ Skill XP restored.")
    print("✅ Gold restored.")
    print("✅ Character XP restored.")

    # ========================================================
    # Final
    # ========================================================

    print("\n" + "=" * 80)
    print("🎉 ALL SKILL UPGRADE SEQUENCE TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())