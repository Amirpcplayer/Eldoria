import asyncio
import sys
from pathlib import Path

# ------------------------------------------------------------------
# PROJECT ROOT
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.skill import Skill

from services.skill_service import (
    get_skill_power,
    get_skill_mana_cost,
)


TEST_LEVELS = list(range(1, 11))


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def print_separator():
    print("-" * 80)


def check_positive(
    name: str,
    value: int,
) -> bool:
    if value <= 0:
        print(f"❌ {name} invalid: {value}")
        return False

    return True


# ------------------------------------------------------------------
# SKILL PROGRESSION
# ------------------------------------------------------------------
def test_skill_progression(skill: Skill) -> bool:
    print_separator()
    print(
        f"🔮 {skill.name} | "
        f"ID={skill.id} | "
        f"Element={skill.element}"
    )

    passed = True
    previous_power = 0
    previous_mana = 0

    print(
        f"Base Power={skill.base_power} | "
        f"Power/Level={skill.power_per_level} | "
        f"Base Mana={skill.mana_cost}"
    )

    print()

    for level in TEST_LEVELS:
        power = get_skill_power(skill, level)
        mana = get_skill_mana_cost(skill, level)

        print(
            f"Lv.{level:2} | "
            f"Power={power:5} | "
            f"Mana={mana:4} | "
            f"Power/Mana={power / mana:.2f}"
        )

        if not check_positive(
            f"{skill.name} Power Lv.{level}",
            power,
        ):
            passed = False

        if not check_positive(
            f"{skill.name} Mana Lv.{level}",
            mana,
        ):
            passed = False

        if level > 1:
            if power < previous_power:
                print(
                    f"❌ Power decreased: "
                    f"{previous_power} → {power}"
                )
                passed = False

            if mana < previous_mana:
                print(
                    f"❌ Mana cost decreased: "
                    f"{previous_mana} → {mana}"
                )
                passed = False

        previous_power = power
        previous_mana = mana

    return passed


# ------------------------------------------------------------------
# SKILL POWER GROWTH
# ------------------------------------------------------------------
def test_power_formula(skill: Skill) -> bool:
    print_separator()
    print(f"🧮 POWER FORMULA TEST: {skill.name}")

    passed = True

    for level in TEST_LEVELS:
        expected = (
            skill.base_power
            + ((level - 1) * skill.power_per_level)
        )

        actual = get_skill_power(
            skill,
            level,
        )

        print(
            f"Lv.{level:2} | "
            f"Expected={expected:5} | "
            f"Actual={actual:5}"
        )

        if actual != expected:
            print("❌ Power formula mismatch.")
            passed = False

    return passed


# ------------------------------------------------------------------
# SKILL MANA FORMULA
# ------------------------------------------------------------------
def test_mana_formula(skill: Skill) -> bool:
    print_separator()
    print(f"🔵 MANA FORMULA TEST: {skill.name}")

    passed = True

    mana_growth = {
        "fire": 8,
        "water": 8,
        "wind": 9,
        "earth": 10,
        "electro": 12,
        "ice": 13,
        "light": 18,
        "dark": 20,
    }.get(skill.element, 0)

    for level in TEST_LEVELS:
        expected = (
            skill.mana_cost
            + ((level - 1) * mana_growth)
        )

        actual = get_skill_mana_cost(
            skill,
            level,
        )

        print(
            f"Lv.{level:2} | "
            f"Growth={mana_growth:2} | "
            f"Expected={expected:4} | "
            f"Actual={actual:4}"
        )

        if actual != expected:
            print("❌ Mana formula mismatch.")
            passed = False

    return passed


# ------------------------------------------------------------------
# POWER / MANA EFFICIENCY
# ------------------------------------------------------------------
def test_efficiency(skill: Skill) -> bool:
    print_separator()
    print(f"⚖️ POWER / MANA EFFICIENCY: {skill.name}")

    passed = True

    efficiencies = []

    for level in TEST_LEVELS:
        power = get_skill_power(
            skill,
            level,
        )

        mana = get_skill_mana_cost(
            skill,
            level,
        )

        efficiency = power / mana
        efficiencies.append(efficiency)

        print(
            f"Lv.{level:2} | "
            f"Power={power:5} | "
            f"Mana={mana:4} | "
            f"Efficiency={efficiency:.3f}"
        )

        if efficiency <= 0:
            print("❌ Invalid efficiency.")
            passed = False

    # جلوگیری از افت شدید Efficiency
    if len(efficiencies) >= 2:
        first = efficiencies[0]
        last = efficiencies[-1]

        change = (
            (last - first) / first
            if first > 0
            else 0
        )

        print(
            f"\nEfficiency Change "
            f"Lv1 → Lv10 = {change * 100:.2f}%"
        )

        if change < -0.60:
            print(
                "❌ Efficiency dropped by more than 60%."
            )
            passed = False

    return passed


# ------------------------------------------------------------------
# ALL SKILLS
# ------------------------------------------------------------------
async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL BALANCE TEST")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Skill)
            .order_by(Skill.id)
        )

        skills = list(result.scalars().all())

    print(f"\nTotal Skills={len(skills)}")

    if not skills:
        print("❌ No skills found.")
        return

    progression_passed = True
    formula_passed = True
    mana_passed = True
    efficiency_passed = True

    # ------------------------------------------------------------------
    # EACH SKILL
    # ------------------------------------------------------------------
    for skill in skills:
        if not test_skill_progression(skill):
            progression_passed = False

        if not test_power_formula(skill):
            formula_passed = False

        if not test_mana_formula(skill):
            mana_passed = False

        if not test_efficiency(skill):
            efficiency_passed = False

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("📊 FINAL RESULT")
    print("=" * 80)

    results = [
        ("Skill Progression", progression_passed),
        ("Power Formula", formula_passed),
        ("Mana Formula", mana_passed),
        ("Power/Mana Efficiency", efficiency_passed),
    ]

    all_passed = True

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {name}")

        if not passed:
            all_passed = False

    print("-" * 80)

    if all_passed:
        print("✅ SKILL BALANCE TEST COMPLETED")
        print("✅ No database values were modified.")
    else:
        print("❌ SKILL BALANCE TEST FAILED")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())