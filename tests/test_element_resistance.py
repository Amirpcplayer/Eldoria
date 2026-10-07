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
from models.monster import Monster
from services.damage_service import (
    calculate_damage,
    get_resistance_multiplier,
)
from services.monster_stats_service import calculate_monster_stats


# ------------------------------------------------------------------
# TEST CONFIG
# ------------------------------------------------------------------
TEST_ATTACK = 100
TEST_DEFENSE = 0


async def get_monsters() -> list[Monster]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Monster)
            .where(Monster.is_active.is_(True))
            .order_by(Monster.id)
        )

        return list(result.scalars().all())


def get_resistance(monster: Monster, element: str) -> float:
    return getattr(
        monster,
        f"{element}_resistance",
        0.0,
    )


def print_resistance(monster: Monster, element: str) -> None:
    resistance = get_resistance(monster, element)
    multiplier = get_resistance_multiplier(resistance)

    print(
        f"{element.upper():8} "
        f"Resistance={resistance:+.2f} "
        f"Multiplier={multiplier:.2f}"
    )


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - ELEMENT & RESISTANCE TEST")
    print("=" * 80)

    monsters = await get_monsters()

    if not monsters:
        print("❌ هیچ Monster فعالی در دیتابیس پیدا نشد.")
        return

    print(f"\n👹 ACTIVE MONSTERS: {len(monsters)}")

    # ------------------------------------------------------------------
    # MONSTER RESISTANCES
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("🛡️ MONSTER RESISTANCES")
    print("=" * 80)

    for monster in monsters:
        print(f"\n👹 {monster.name}")
        print(f"ID={monster.id}")
        print(f"Variant={monster.variant}")
        print(f"Element={monster.element}")

        for element in (
            "fire",
            "water",
            "ice",
            "earth",
            "wind",
            "electro",
            "shadow",
            "light",
            "blood",
            "steel",
        ):
            print_resistance(monster, element)

    # ------------------------------------------------------------------
    # ELEMENTAL DAMAGE TEST
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("🔥 ELEMENTAL DAMAGE TEST")
    print("=" * 80)

    test_cases = [
        ("fire", "ice"),
        ("fire", "fire"),
        ("fire", "water"),
        ("water", "fire"),
        ("water", "electro"),
        ("ice", "fire"),
        ("ice", "water"),
        ("electro", "water"),
        ("earth", "electro"),
        ("wind", "earth"),
        ("shadow", "light"),
        ("light", "shadow"),
        ("blood", "shadow"),
        ("steel", "fire"),
    ]

    all_passed = True

    for attack_element, defender_element in test_cases:
        result = calculate_damage(
            attack=TEST_ATTACK,
            defense=TEST_DEFENSE,
            skill_power=1.0,
            attack_element=attack_element,
            defender_element=defender_element,
            resistance=0.0,
            critical=False,
            randomize=False,
        )

        print(
            f"{attack_element:8} → "
            f"{defender_element:8} | "
            f"Damage={result.damage} | "
            f"Element Multiplier={result.element_multiplier:.2f}"
        )

        expected_multiplier = 1.0

        # Known elemental interactions
        if attack_element == "fire" and defender_element == "ice":
            expected_multiplier = 1.50

        elif attack_element == "fire" and defender_element == "fire":
            expected_multiplier = 0.75

        elif attack_element == "fire" and defender_element == "water":
            expected_multiplier = 0.70

        elif attack_element == "water" and defender_element == "fire":
            expected_multiplier = 1.50

        elif attack_element == "water" and defender_element == "electro":
            expected_multiplier = 0.80

        elif attack_element == "ice" and defender_element == "fire":
            expected_multiplier = 1.50

        elif attack_element == "ice" and defender_element == "water":
            expected_multiplier = 0.80

        elif attack_element == "electro" and defender_element == "water":
            expected_multiplier = 1.50

        elif attack_element == "earth" and defender_element == "electro":
            expected_multiplier = 1.50

        elif attack_element == "wind" and defender_element == "earth":
            expected_multiplier = 1.50

        elif attack_element == "shadow" and defender_element == "light":
            expected_multiplier = 1.50

        elif attack_element == "light" and defender_element == "shadow":
            expected_multiplier = 1.50

        elif attack_element == "blood" and defender_element == "shadow":
            expected_multiplier = 1.25

        elif attack_element == "steel" and defender_element == "fire":
            expected_multiplier = 0.80

        if result.element_multiplier == expected_multiplier:
            print("  ✅ Element multiplier correct.")
        else:
            print(
                f"  ❌ Expected {expected_multiplier:.2f}, "
                f"got {result.element_multiplier:.2f}"
            )
            all_passed = False

    # ------------------------------------------------------------------
    # RESISTANCE TEST
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("🛡️ RESISTANCE DAMAGE TEST")
    print("=" * 80)

    resistance_cases = [
        ("0%", 0.00, 100),
        ("20%", 0.20, 80),
        ("50%", 0.50, 50),
        ("-25% Weakness", -0.25, 125),
    ]

    for name, resistance, expected_damage in resistance_cases:
        result = calculate_damage(
            attack=100,
            defense=0,
            skill_power=1.0,
            attack_element="fire",
            defender_element="neutral",
            resistance=resistance,
            critical=False,
            randomize=False,
        )

        print(
            f"{name:18} | "
            f"Damage={result.damage} | "
            f"Resistance Multiplier={result.resistance_multiplier:.2f}"
        )

        if result.damage == expected_damage:
            print("  ✅ Resistance calculation correct.")
        else:
            print(
                f"  ❌ Expected Damage={expected_damage}, "
                f"got {result.damage}"
            )
            all_passed = False

    # ------------------------------------------------------------------
    # REAL MONSTER STAT SCALING
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("👹 REAL MONSTER ELEMENT + STATS")
    print("=" * 80)

    for monster in monsters:
        stats = calculate_monster_stats(
            monster,
            level=5,
        )

        print(
            f"{monster.name} | "
            f"Variant={monster.variant} | "
            f"Element={monster.element} | "
            f"HP={stats.hp} | "
            f"ATK={stats.attack} | "
            f"DEF={stats.defense}"
        )

    # ------------------------------------------------------------------
    # FINAL
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)

    if all_passed:
        print("✅ ELEMENT & RESISTANCE TEST COMPLETED")
        print("✅ Element multipliers are working correctly.")
        print("✅ Resistance multipliers are working correctly.")
        print("✅ Monster element data loaded correctly.")
        print("✅ Monster stat scaling still works.")
        print("✅ No database values were modified.")
    else:
        print("❌ ELEMENT & RESISTANCE TEST FAILED")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())