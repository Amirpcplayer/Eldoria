import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)


# ============================================================
# IMPORTS
# ============================================================

from services.power_service import (
    get_hero_base_stats,
    scale_monster_stats,
)


# ============================================================
# HERO
# ============================================================

def print_hero(level: int) -> None:

    stats = get_hero_base_stats(level)

    print(
        f"Hero Lv.{level} | "
        f"HP={stats.hp} | "
        f"ATK={stats.attack} | "
        f"DEF={stats.defense} | "
        f"MDEF={stats.magic_defense}"
    )


# ============================================================
# MONSTER
# ============================================================

def print_monster(
    name: str,
    level: int,
    base_hp: int,
    base_attack: int,
    base_defense: int,
    power_multiplier: float = 1.0,
) -> None:

    stats = scale_monster_stats(
        base_hp=base_hp,
        base_attack=base_attack,
        base_magic_power=10,
        base_defense=base_defense,
        base_magic_defense=8,
        base_speed=10,
        base_accuracy=10,
        base_luck=5,
        base_critical=5,
        level=level,
        power_multiplier=power_multiplier,
    )

    print(
        f"{name} Lv.{level} | "
        f"HP={stats.hp} | "
        f"ATK={stats.attack} | "
        f"DEF={stats.defense}"
    )


# ============================================================
# TEST
# ============================================================

def main() -> None:

    print("=" * 60)
    print("HERO POWER CURVE")
    print("=" * 60)

    for level in (1, 3, 5, 10, 20):
        print_hero(level)

    print()
    print("=" * 60)
    print("MONSTER POWER CURVE")
    print("=" * 60)

    monsters = [
        ("🐺 Normal Wolf", 100, 12, 8, 1.00),
        ("🐺 Ice Wolf", 115, 11, 10, 1.08),
        ("🐺 Fire Wolf", 105, 15, 7, 1.08),
        ("🐺 Storm Wolf", 120, 16, 8, 1.25),
        ("🐺 Alpha Wolf", 220, 25, 16, 1.70),
    ]

    for name, hp, attack, defense, multiplier in monsters:

        for level in (1, 3, 5, 10):

            print_monster(
                name=name,
                level=level,
                base_hp=hp,
                base_attack=attack,
                base_defense=defense,
                power_multiplier=multiplier,
            )

        print("-" * 60)


if __name__ == "__main__":
    main()