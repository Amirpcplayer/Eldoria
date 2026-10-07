import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character

from services.skill_service import (
    get_character_skills,
    get_skill_power,
    get_skill_upgrade_info,
    upgrade_skill,
)
from services.xp_service import add_skill_xp


# ============================================================
# Helpers
# ============================================================

async def get_test_character() -> Character | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character)
            .order_by(Character.id)
            .limit(1)
        )


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL XP PROGRESSION TEST")
    print("=" * 80)

    # --------------------------------------------------------
    # Character
    # --------------------------------------------------------

    character = await get_test_character()

    if character is None:
        print("❌ No character found.")
        return

    telegram_id = character.telegram_id
    character_id = character.id

    print("\n" + "=" * 80)
    print("👤 CHARACTER")
    print("-" * 80)

    print(f"ID={character.id}")
    print(f"Name={character.name}")
    print(f"Level={character.level}")
    print(f"XP={character.xp}")
    print(f"Skill XP={character.skill_xp}")
    print(f"Gold={character.gold}")

    # --------------------------------------------------------
    # Skill
    # --------------------------------------------------------

    skills = await get_character_skills(character_id)

    if not skills:
        print("\n❌ Character has no learned skills.")
        return

    skill, character_skill = skills[0]

    skill_id = skill.id

    print("\n" + "=" * 80)
    print("🔮 TEST SKILL")
    print("-" * 80)

    print(f"Name={skill.name}")
    print(f"Skill ID={skill.id}")
    print(f"Element={skill.element}")
    print(f"Current Level={character_skill.level}")
    print(f"Max Level={skill.max_level}")

    # --------------------------------------------------------
    # Save initial state
    # --------------------------------------------------------

    initial_level = character_skill.level
    initial_character_xp = character.xp
    initial_skill_xp = character.skill_xp
    initial_gold = character.gold

    # --------------------------------------------------------
    # Upgrade Info
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("📋 UPGRADE INFO")
    print("-" * 80)

    success, message, info = await get_skill_upgrade_info(
        telegram_id,
        skill_id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if not success or info is None:
        print("❌ Could not get upgrade information.")
        return

    print(f"Current Level={info['current_level']}")
    print(f"Next Level={info['next_level']}")
    print(f"XP Cost={info['xp_cost']}")
    print(f"Gold Cost={info['gold_cost']}")
    print(f"Current Skill XP={info['current_xp']}")
    print(f"Current Gold={info['current_gold']}")
    print(f"Can Upgrade={info['can_upgrade']}")

    # --------------------------------------------------------
    # Test 1: Insufficient Resources
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("🧪 TEST 1 - INSUFFICIENT RESOURCES")
    print("-" * 80)

    cost_xp = info["xp_cost"]
    cost_gold = info["gold_cost"]

    # Current resources should be checked naturally.
    # We intentionally do NOT modify the database here.

    if initial_skill_xp < cost_xp or initial_gold < cost_gold:

        success, message = await upgrade_skill(
            telegram_id,
            skill_id,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        if success:
            print("❌ Upgrade succeeded despite insufficient resources.")
            return

        print("✅ Upgrade correctly blocked.")

    else:
        print("ℹ️ Character currently has enough resources.")
        print("Skipping insufficient-resource assertion.")

    # --------------------------------------------------------
    # Test 2: Add exact required Skill XP
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("🧪 TEST 2 - SKILL XP ADDITION")
    print("-" * 80)

    xp_to_add = cost_xp

    before_add_skill_xp = initial_skill_xp

    success, new_skill_xp = await add_skill_xp(
        telegram_id,
        xp_to_add,
    )

    print(f"Success={success}")
    print(f"Skill XP Before={before_add_skill_xp}")
    print(f"Skill XP Added={xp_to_add}")
    print(f"Skill XP After={new_skill_xp}")

    if not success:
        print("❌ add_skill_xp failed.")
        return

    expected_skill_xp = before_add_skill_xp + xp_to_add

    if new_skill_xp != expected_skill_xp:
        print(
            "❌ Skill XP amount is incorrect."
        )
        print(
            f"Expected={expected_skill_xp}"
        )
        print(
            f"Actual={new_skill_xp}"
        )
        return

    print("✅ Skill XP addition is correct.")

    # --------------------------------------------------------
    # Refresh character state
    # --------------------------------------------------------

    character = await get_test_character()

    if character is None:
        print("❌ Character disappeared.")
        return

    # --------------------------------------------------------
    # Test 3: Upgrade Skill
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("🧪 TEST 3 - SKILL UPGRADE")
    print("-" * 80)

    before_upgrade_level = character_skill.level
    before_upgrade_skill_xp = character.skill_xp
    before_upgrade_gold = character.gold
    before_upgrade_character_xp = character.xp

    success, message = await upgrade_skill(
        telegram_id,
        skill_id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if not success:
        print("❌ Skill upgrade failed.")
        return

    # --------------------------------------------------------
    # Reload character + skill
    # --------------------------------------------------------

    character = await get_test_character()

    if character is None:
        print("❌ Character disappeared after upgrade.")
        return

    skills_after = await get_character_skills(
        character.id
    )

    target_skill = None

    for loaded_skill, loaded_character_skill in skills_after:
        if loaded_skill.id == skill_id:
            target_skill = (
                loaded_skill,
                loaded_character_skill,
            )
            break

    if target_skill is None:
        print("❌ Upgraded skill could not be reloaded.")
        return

    skill_after, character_skill_after = target_skill

    # --------------------------------------------------------
    # Assertions
    # --------------------------------------------------------

    expected_level = before_upgrade_level + 1
    expected_skill_xp_after = (
        before_upgrade_skill_xp - cost_xp
    )
    expected_gold_after = (
        before_upgrade_gold - cost_gold
    )

    print("\n" + "=" * 80)
    print("📊 UPGRADE RESULT")
    print("-" * 80)

    print(
        f"Level: "
        f"{before_upgrade_level} -> "
        f"{character_skill_after.level}"
    )

    print(
        f"Skill XP: "
        f"{before_upgrade_skill_xp} -> "
        f"{character.skill_xp}"
    )

    print(
        f"Gold: "
        f"{before_upgrade_gold} -> "
        f"{character.gold}"
    )

    print(
        f"Character XP: "
        f"{before_upgrade_character_xp} -> "
        f"{character.xp}"
    )

    if character_skill_after.level != expected_level:
        print("❌ Skill level did not increase correctly.")
        return

    if character.skill_xp != expected_skill_xp_after:
        print("❌ Skill XP was not consumed correctly.")
        return

    if character.gold != expected_gold_after:
        print("❌ Gold was not consumed correctly.")
        return

    if character.xp != before_upgrade_character_xp:
        print("❌ Character XP changed unexpectedly.")
        return

    print("✅ Skill level increased correctly.")
    print("✅ Skill XP consumed correctly.")
    print("✅ Gold consumed correctly.")
    print("✅ Character XP remained unchanged.")

    # --------------------------------------------------------
    # Test 4: Skill Power Growth
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("🧪 TEST 4 - SKILL POWER GROWTH")
    print("-" * 80)

    old_power = get_skill_power(
        skill_after,
        before_upgrade_level,
    )

    new_power = get_skill_power(
        skill_after,
        character_skill_after.level,
    )

    print(
        f"Power: "
        f"{old_power} -> "
        f"{new_power}"
    )

    if new_power <= old_power:
        print("❌ Skill power did not increase.")
        return

    print("✅ Skill power increased correctly.")

    # --------------------------------------------------------
    # Test 5: Upgrade Info After Upgrade
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("🧪 TEST 5 - POST-UPGRADE INFO")
    print("-" * 80)

    success, message, info_after = await get_skill_upgrade_info(
        telegram_id,
        skill_id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if not success or info_after is None:
        print("❌ Could not load post-upgrade information.")
        return

    print(
        f"Current Level={info_after['current_level']}"
    )

    print(
        f"Next Level={info_after['next_level']}"
    )

    print(
        f"XP Cost={info_after['xp_cost']}"
    )

    print(
        f"Gold Cost={info_after['gold_cost']}"
    )

    if (
        info_after["current_level"]
        != character_skill_after.level
    ):
        print("❌ Upgrade info level is incorrect.")
        return

    print("✅ Post-upgrade information is correct.")

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("🎉 ALL SKILL XP PROGRESSION TESTS PASSED")
    print("=" * 80)

    print(
        f"Skill: {skill_after.name}"
    )

    print(
        f"Level: "
        f"{initial_level} -> "
        f"{character_skill_after.level}"
    )

    print(
        f"Skill XP: "
        f"{initial_skill_xp} -> "
        f"{character.skill_xp}"
    )

    print(
        f"Gold: "
        f"{initial_gold} -> "
        f"{character.gold}"
    )

    print(
        f"Character XP: "
        f"{initial_character_xp} -> "
        f"{character.xp}"
    )


if __name__ == "__main__":
    asyncio.run(main())