import asyncio
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.skill import Skill
from services.skill_service import (
    get_skill_mana_cost,
    SKILL_MANA_GROWTH,
)


TEST_SKILL_IDS = list(range(1, 9))


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL MANA SCALING TEST")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Skill)
            .where(
                Skill.id.in_(TEST_SKILL_IDS),
                Skill.is_active.is_(True),
            )
            .order_by(Skill.id)
        )

        skills = list(result.scalars().all())

    if not skills:
        print("❌ No active test skills found.")
        return

    print("\n" + "=" * 80)
    print("🔮 ACTIVE SKILLS")
    print("-" * 80)

    for skill in skills:
        growth = SKILL_MANA_GROWTH.get(skill.element, 0)

        print(
            f"ID={skill.id} | "
            f"{skill.name} | "
            f"Element={skill.element} | "
            f"Base Mana={skill.mana_cost} | "
            f"Growth={growth}"
        )

    # =================================================================
    # TEST 1 - Level 1 Mana Cost
    # =================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 1 - LEVEL 1 MANA COST")
    print("-" * 80)

    for skill in skills:
        mana = get_skill_mana_cost(skill, 1)

        print(
            f"{skill.name} | "
            f"Lv.1 Mana={mana} | "
            f"Expected={skill.mana_cost}"
        )

        assert mana == skill.mana_cost

    print("✅ Level 1 Mana costs are correct.")

    # =================================================================
    # TEST 2 - Mana Growth
    # =================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 2 - MANA GROWTH")
    print("-" * 80)

    for skill in skills:
        growth = SKILL_MANA_GROWTH.get(skill.element, 0)

        print(f"\n🔮 {skill.name}")
        print(
            f"Element={skill.element} | "
            f"Base={skill.mana_cost} | "
            f"Growth={growth}"
        )

        previous_mana = None

        for level in range(1, skill.max_level + 1):
            mana = get_skill_mana_cost(skill, level)

            expected = (
                skill.mana_cost
                + ((level - 1) * growth)
            )

            print(
                f"Lv.{level:2d} | "
                f"Mana={mana:3d} | "
                f"Expected={expected:3d}"
            )

            assert mana == expected

            if previous_mana is not None:
                assert mana >= previous_mana

            previous_mana = mana

    print("\n✅ Mana growth is correct for all tested skills.")

    # =================================================================
    # TEST 3 - Element-specific Mana Growth
    # =================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 3 - ELEMENT-SPECIFIC MANA GROWTH")
    print("-" * 80)

    expected_growth = {
        "fire": 8,
        "water": 8,
        "wind": 9,
        "earth": 10,
        "electro": 12,
        "ice": 13,
        "light": 18,
        "dark": 20,
    }

    for skill in skills:
        actual_growth = SKILL_MANA_GROWTH.get(
            skill.element,
            0,
        )

        expected_growth_value = expected_growth.get(
            skill.element
        )

        print(
            f"{skill.name} | "
            f"Element={skill.element} | "
            f"Actual Growth={actual_growth} | "
            f"Expected Growth={expected_growth_value}"
        )

        assert expected_growth_value is not None
        assert actual_growth == expected_growth_value

    print("✅ Element-specific Mana growth is correct.")

    # =================================================================
    # TEST 4 - Level 10 Mana Cost
    # =================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 4 - LEVEL 10 MANA COST")
    print("-" * 80)

    for skill in skills:
        growth = SKILL_MANA_GROWTH.get(skill.element, 0)

        mana = get_skill_mana_cost(
            skill,
            skill.max_level,
        )

        expected = (
            skill.mana_cost
            + ((skill.max_level - 1) * growth)
        )

        print(
            f"{skill.name} | "
            f"Lv.{skill.max_level} Mana={mana} | "
            f"Expected={expected}"
        )

        assert mana == expected

    print("✅ Level 10 Mana costs are correct.")

    # =================================================================
    # TEST 5 - Invalid / Low Levels
    # =================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 5 - INVALID / LOW LEVELS")
    print("-" * 80)

    for skill in skills:
        level_1_mana = get_skill_mana_cost(skill, 1)

        level_0_mana = get_skill_mana_cost(skill, 0)
        level_negative_mana = get_skill_mana_cost(skill, -5)

        print(
            f"{skill.name} | "
            f"Lv.0={level_0_mana} | "
            f"Lv.-5={level_negative_mana} | "
            f"Lv.1={level_1_mana}"
        )

        assert level_0_mana == level_1_mana
        assert level_negative_mana == level_1_mana

    print("✅ Invalid low levels safely resolve to Level 1.")

    # =================================================================
    # TEST 6 - High Levels
    # =================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 6 - HIGH LEVEL CALCULATION")
    print("-" * 80)

    for skill in skills:
        growth = SKILL_MANA_GROWTH.get(skill.element, 0)

        level_20_mana = get_skill_mana_cost(
            skill,
            20,
        )

        expected = (
            skill.mana_cost
            + (19 * growth)
        )

        print(
            f"{skill.name} | "
            f"Lv.20 Mana={level_20_mana} | "
            f"Expected={expected}"
        )

        assert level_20_mana == expected

    print("✅ High-level Mana calculation is correct.")

    # =================================================================
    # TEST 7 - No Database Mutation
    # =================================================================
    print("\n" + "=" * 80)
    print("🧪 TEST 7 - DATABASE IMMUTABILITY")
    print("-" * 80)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Skill)
            .where(
                Skill.id.in_(TEST_SKILL_IDS)
            )
            .order_by(Skill.id)
        )

        skills_after = list(result.scalars().all())

    assert len(skills_after) == len(skills)

    for before, after in zip(skills, skills_after):
        assert before.id == after.id
        assert before.mana_cost == after.mana_cost
        assert before.element == after.element
        assert before.max_level == after.max_level

    print("✅ Mana calculations did not mutate database values.")

    print("\n" + "=" * 80)
    print("🎉 ALL SKILL MANA SCALING TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())