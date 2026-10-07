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
    get_skill_upgrade_info,
    upgrade_skill,
    get_skill_power,
    get_upgrade_cost,
)


TEST_CHARACTER_NAME = "Anos Voldigoad"
TEST_SKILL_ID = 1

TEST_SKILL_XP = 100_000
TEST_SKILL_GOLD = 200_000


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL UPGRADE FLOW TEST")
    print("=" * 80)

    # =================================================================
    # LOAD CHARACTER + SAVE ORIGINAL STATE
    # =================================================================
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.name == TEST_CHARACTER_NAME
            )
        )

        if character is None:
            print("❌ Character not found.")
            return

        skill = await session.scalar(
            select(Skill).where(
                Skill.id == TEST_SKILL_ID
            )
        )

        if skill is None:
            print("❌ Test skill not found.")
            return

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == TEST_SKILL_ID,
            )
        )

        if character_skill is None:
            print("❌ Character does not have the test skill.")
            return

        original_character = {
            "level": character.level,
            "xp": character.xp,
            "skill_xp": character.skill_xp,
            "gold": character.gold,
        }

        original_skill = {
            "level": character_skill.level,
            "slot": character_skill.slot,
            "unlocked": character_skill.unlocked,
        }

        character_id = character.id
        telegram_id = character.telegram_id

        print("\n" + "=" * 80)
        print("👤 CHARACTER")
        print("-" * 80)
        print(f"ID={character.id}")
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
        print(
            f"Current Power="
            f"{get_skill_power(skill, character_skill.level)}"
        )

    try:
        # =============================================================
        # PREPARE TEST STATE
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 PREPARING TEST STATE")
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
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            assert character is not None
            assert character_skill is not None

            character_skill.level = 1
            character_skill.unlocked = True
            character_skill.slot = 1

            character.skill_xp = TEST_SKILL_XP
            character.gold = TEST_SKILL_GOLD

            await session.commit()

        print("Skill Level=1")
        print(f"Skill XP={TEST_SKILL_XP:,}")
        print(f"Gold={TEST_SKILL_GOLD:,}")
        print("✅ Test state prepared.")

        # =============================================================
        # TEST 1 - Upgrade info
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 1 - UPGRADE INFO")
        print("-" * 80)

        success, message, info = await get_skill_upgrade_info(
            telegram_id,
            TEST_SKILL_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is True
        assert info is not None

        print(f"Current Level={info['current_level']}")
        print(f"Next Level={info['next_level']}")
        print(f"Current Power={info['current_power']}")
        print(f"Next Power={info['next_power']}")
        print(f"XP Cost={info['xp_cost']}")
        print(f"Gold Cost={info['gold_cost']}")
        print(f"Can Upgrade={info['can_upgrade']}")

        assert info["current_level"] == 1
        assert info["next_level"] == 2
        assert info["current_power"] == get_skill_power(skill, 1)
        assert info["next_power"] == get_skill_power(skill, 2)

        cost = get_upgrade_cost(1)

        assert cost is not None
        assert info["xp_cost"] == cost["xp"]
        assert info["gold_cost"] == cost["gold"]
        assert info["can_upgrade"] is True

        print("✅ Upgrade info correct.")

        # =============================================================
        # TEST 2 - Level 1 -> 2
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 2 - UPGRADE 1 → 2")
        print("-" * 80)

        before_skill_xp = TEST_SKILL_XP
        before_gold = TEST_SKILL_GOLD

        cost = get_upgrade_cost(1)
        assert cost is not None

        success, message = await upgrade_skill(
            telegram_id,
            TEST_SKILL_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is True

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == character_id
                )
            )

            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character_id,
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            assert character is not None
            assert character_skill is not None

            print(f"New Skill Level={character_skill.level}")
            print(f"Remaining Skill XP={character.skill_xp}")
            print(f"Remaining Gold={character.gold}")

            assert character_skill.level == 2
            assert character.skill_xp == (
                before_skill_xp - cost["xp"]
            )
            assert character.gold == (
                before_gold - cost["gold"]
            )

        print("✅ Level 1 → 2 upgrade correct.")

        # =============================================================
        # TEST 3 - Sequential upgrades to Level 10
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 3 - SEQUENTIAL UPGRADES")
        print("-" * 80)

        expected_level = 2

        while expected_level < skill.max_level:
            cost = get_upgrade_cost(expected_level)

            assert cost is not None

            async with AsyncSessionLocal() as session:
                character = await session.scalar(
                    select(Character).where(
                        Character.id == character_id
                    )
                )

                assert character is not None

                before_xp = character.skill_xp
                before_gold = character.gold

            success, message = await upgrade_skill(
                telegram_id,
                TEST_SKILL_ID,
            )

            print(
                f"Lv.{expected_level} → "
                f"Lv.{expected_level + 1} | "
                f"XP -{cost['xp']:,} | "
                f"Gold -{cost['gold']:,} | "
                f"Success={success}"
            )

            assert success is True

            async with AsyncSessionLocal() as session:
                character_skill = await session.scalar(
                    select(CharacterSkill).where(
                        CharacterSkill.character_id == character_id,
                        CharacterSkill.skill_id == TEST_SKILL_ID,
                    )
                )

                character = await session.scalar(
                    select(Character).where(
                        Character.id == character_id
                    )
                )

                assert character_skill is not None
                assert character is not None

                assert character_skill.level == (
                    expected_level + 1
                )

                assert character.skill_xp == (
                    before_xp - cost["xp"]
                )

                assert character.gold == (
                    before_gold - cost["gold"]
                )

            expected_level += 1

        async with AsyncSessionLocal() as session:
            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character_id,
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            assert character_skill is not None
            assert character_skill.level == skill.max_level

        print(f"Final Skill Level={skill.max_level}")
        print("✅ Sequential upgrades to Max Level succeeded.")

        # =============================================================
        # TEST 4 - Max level protection
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 4 - MAX LEVEL PROTECTION")
        print("-" * 80)

        success, message, info = await get_skill_upgrade_info(
            telegram_id,
            TEST_SKILL_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")
        print(f"Info={info}")

        assert success is False
        assert info is None
        assert "حداکثر" in message

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == character_id
                )
            )

            assert character is not None

            before_xp = character.skill_xp
            before_gold = character.gold

        success, message = await upgrade_skill(
            telegram_id,
            TEST_SKILL_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is False

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == character_id
                )
            )

            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character_id,
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            assert character is not None
            assert character_skill is not None

            assert character_skill.level == skill.max_level
            assert character.skill_xp == before_xp
            assert character.gold == before_gold

        print("✅ Max level correctly blocks upgrade.")

        # =============================================================
        # TEST 5 - Insufficient Skill XP
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 5 - INSUFFICIENT SKILL XP")
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
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            assert character is not None
            assert character_skill is not None

            character_skill.level = 1
            character.skill_xp = 499
            character.gold = TEST_SKILL_GOLD

            await session.commit()

        before_xp = 499
        before_gold = TEST_SKILL_GOLD

        success, message = await upgrade_skill(
            telegram_id,
            TEST_SKILL_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is False

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == character_id
                )
            )

            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character_id,
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            assert character is not None
            assert character_skill is not None

            assert character_skill.level == 1
            assert character.skill_xp == before_xp
            assert character.gold == before_gold

        print("✅ Insufficient Skill XP correctly blocked.")

        # =============================================================
        # TEST 6 - Insufficient Gold
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 6 - INSUFFICIENT GOLD")
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
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            assert character is not None
            assert character_skill is not None

            character_skill.level = 1
            character.skill_xp = TEST_SKILL_XP
            character.gold = 999

            await session.commit()

        before_xp = TEST_SKILL_XP
        before_gold = 999

        success, message = await upgrade_skill(
            telegram_id,
            TEST_SKILL_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is False

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.id == character_id
                )
            )

            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character_id,
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            assert character is not None
            assert character_skill is not None

            assert character_skill.level == 1
            assert character.skill_xp == before_xp
            assert character.gold == before_gold

        print("✅ Insufficient Gold correctly blocked.")

        # =============================================================
        # TEST 7 - Power progression
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 7 - POWER PROGRESSION")
        print("-" * 80)

        for level in range(1, skill.max_level + 1):
            power = get_skill_power(skill, level)

            expected_power = (
                skill.base_power
                + ((level - 1) * skill.power_per_level)
            )

            print(
                f"Lv.{level:2d} | "
                f"Power={power:4d} | "
                f"Expected={expected_power:4d}"
            )

            assert power == expected_power

        print("✅ Skill power progression correct.")

        # =============================================================
        # TEST 8 - Failed upgrades preserve resources
        # =============================================================
        print("\n" + "=" * 80)
        print("🧪 TEST 8 - FAILED UPGRADE RESOURCE PROTECTION")
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
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            assert character is not None
            assert character_skill is not None

            print(f"Skill Level={character_skill.level}")
            print(f"Skill XP={character.skill_xp}")
            print(f"Gold={character.gold}")

            assert character_skill.level == 1
            assert character.skill_xp == TEST_SKILL_XP
            assert character.gold == 999

        print("✅ Failed upgrades did not consume resources.")

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
                    Character.id == character_id
                )
            )

            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character_id,
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            if character is not None:
                character.level = original_character["level"]
                character.xp = original_character["xp"]
                character.skill_xp = original_character["skill_xp"]
                character.gold = original_character["gold"]

            if character_skill is not None:
                character_skill.level = original_skill["level"]
                character_skill.slot = original_skill["slot"]
                character_skill.unlocked = original_skill["unlocked"]

            await session.commit()

        print("✅ Database state restored.")

    print("\n" + "=" * 80)
    print("🎉 ALL SKILL UPGRADE FLOW TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())