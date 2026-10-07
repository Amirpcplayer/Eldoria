import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.damage_service import (
    calculate_damage,
)


def print_test(
    title: str,
    attack: int,
    defense: int,
    skill_power: float = 1.0,
    attack_element: str = "neutral",
    defender_element: str = "neutral",
    resistance: float = 0.0,
    critical: bool = False,
) -> None:

    result = calculate_damage(
        attack=attack,
        defense=defense,
        skill_power=skill_power,
        attack_element=attack_element,
        defender_element=defender_element,
        resistance=resistance,
        critical=critical,
        randomize=False,
    )

    print(f"🧪 {title}")
    print(
        f"   ATK={attack} | "
        f"DEF={defense} | "
        f"Skill={skill_power} | "
        f"Element={attack_element}->{defender_element}"
    )

    print(
        f"   Base Damage={result.base_damage:.2f}"
    )

    print(
        f"   Defense Multiplier="
        f"{result.defense_multiplier:.3f}"
    )

    print(
        f"   Element Multiplier="
        f"{result.element_multiplier:.2f}"
    )

    print(
        f"   Resistance Multiplier="
        f"{result.resistance_multiplier:.2f}"
    )

    print(
        f"   Critical={result.critical}"
    )

    print(
        f"   ⚔️ FINAL DAMAGE={result.damage}"
    )

    print("-" * 70)


def main() -> None:
    print("=" * 70)
    print("WORLD ELDORIA - DAMAGE ENGINE TEST")
    print("=" * 70)

    # 1
    print_test(
        title="Normal Attack",
        attack=10,
        defense=8,
    )

    # 2
    print_test(
        title="High Defense",
        attack=10,
        defense=100,
    )

    # 3
    print_test(
        title="Very High Defense",
        attack=100,
        defense=900,
    )

    # 4
    print_test(
        title="Fire -> Ice Weakness",
        attack=20,
        defense=10,
        attack_element="fire",
        defender_element="ice",
    )

    # 5
    print_test(
        title="Fire -> Fire Resistance",
        attack=20,
        defense=10,
        attack_element="fire",
        defender_element="fire",
    )

    # 6
    print_test(
        title="Fire -> Water",
        attack=20,
        defense=10,
        attack_element="fire",
        defender_element="water",
    )

    # 7
    print_test(
        title="20% Resistance",
        attack=20,
        defense=10,
        resistance=0.20,
    )

    # 8
    print_test(
        title="25% Weakness",
        attack=20,
        defense=10,
        resistance=-0.25,
    )

    # 9
    print_test(
        title="Critical Hit",
        attack=20,
        defense=10,
        critical=True,
    )

    # 10
    print_test(
        title="Skill Power 2.0",
        attack=20,
        defense=10,
        skill_power=2.0,
    )

    print()
    print("=" * 70)
    print("✅ DAMAGE ENGINE TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()