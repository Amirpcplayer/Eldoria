from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import AsyncSessionLocal
from models.monster import Monster

from services.power_service import (
    get_hero_base_stats,
    scale_monster_stats,
)

from services.damage_service import calculate_damage


TEST_LEVELS = [1, 5, 10, 20, 50, 100]


def print_separator() -> None:
    print("-" * 80)


def validate_positive(name: str, value: int) -> None:
    assert value > 0, f"{name} invalid: {value}"
    print(f"✅ {name}: {value}")


def _run_hero_scaling() -> None:
    print("\n" + "=" * 80)
    print("🧪 HERO LEVEL SCALING")
    print("=" * 80)

    previous = None

    for level in TEST_LEVELS:
        stats = get_hero_base_stats(level)

        print(
            f"Lv.{level:3} | "
            f"HP={stats.hp:4} | "
            f"Mana={stats.mana:4} | "
            f"ATK={stats.attack:3} | "
            f"Magic={stats.magic_power:3} | "
            f"DEF={stats.defense:3} | "
            f"MDEF={stats.magic_defense:3} | "
            f"SPD={stats.speed:3} | "
            f"ACC={stats.accuracy:3} | "
            f"LUCK={stats.luck:2} | "
            f"CRIT={stats.critical:2}"
        )

        values = [
            stats.hp,
            stats.mana,
            stats.attack,
            stats.magic_power,
            stats.defense,
            stats.magic_defense,
            stats.speed,
            stats.accuracy,
            stats.luck,
            stats.critical,
        ]

        stat_names = [
            "HP",
            "Mana",
            "ATK",
            "Magic Power",
            "DEF",
            "MDEF",
            "Speed",
            "Accuracy",
            "Luck",
            "Critical",
        ]

        for stat_name, value in zip(stat_names, values):
            assert value > 0, (
                f"{stat_name} invalid at Level {level}: {value}"
            )

        if previous is not None:
            previous_values = [
                previous.hp,
                previous.mana,
                previous.attack,
                previous.magic_power,
                previous.defense,
                previous.magic_defense,
                previous.speed,
                previous.accuracy,
                previous.luck,
                previous.critical,
            ]

            for old, new, stat_name in zip(
                previous_values,
                values,
                stat_names,
            ):
                assert new >= old, (
                    f"{stat_name} decreased: "
                    f"{old} → {new}"
                )

        previous = stats


@pytest.mark.asyncio
async def test_hero_scaling() -> None:
    _run_hero_scaling()


async def _run_monster_scaling() -> None:
    print("\n" + "=" * 80)
    print("🧪 MONSTER LEVEL SCALING")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Monster)
            .where(Monster.is_active.is_(True))
            .order_by(Monster.id)
        )

        monsters = list(result.scalars().all())

    print(f"Active Monsters={len(monsters)}")

    assert monsters, "No active monsters found."

    for monster in monsters:
        print_separator()

        print(
            f"👹 {monster.name} | "
            f"{monster.variant} | "
            f"Power x{monster.power_multiplier}"
        )

        previous_hp = 0
        previous_attack = 0
        previous_defense = 0

        for level in TEST_LEVELS:
            stats = scale_monster_stats(
                base_hp=monster.base_hp,
                base_attack=monster.base_attack,
                base_magic_power=monster.base_magic_power,
                base_defense=monster.base_defense,
                base_magic_defense=monster.base_magic_defense,
                base_speed=monster.base_speed,
                base_accuracy=monster.base_accuracy,
                base_luck=monster.base_luck,
                base_critical=monster.base_critical,
                level=level,
                power_multiplier=monster.power_multiplier,
            )

            print(
                f"Lv.{level:3} | "
                f"HP={stats.hp:5} | "
                f"ATK={stats.attack:4} | "
                f"DEF={stats.defense:4} | "
                f"MDEF={stats.magic_defense:4}"
            )

            assert stats.hp >= previous_hp, (
                f"HP decreased for {monster.variant}: "
                f"{previous_hp} → {stats.hp}"
            )

            assert stats.attack >= previous_attack, (
                f"Attack decreased for {monster.variant}: "
                f"{previous_attack} → {stats.attack}"
            )

            assert stats.defense >= previous_defense, (
                f"Defense decreased for {monster.variant}: "
                f"{previous_defense} → {stats.defense}"
            )

            previous_hp = stats.hp
            previous_attack = stats.attack
            previous_defense = stats.defense


@pytest.mark.asyncio
async def test_monster_scaling() -> None:
    await _run_monster_scaling()


def _run_damage_balance() -> None:
    print("\n" + "=" * 80)
    print("🧪 DAMAGE BALANCE")
    print("=" * 80)

    for level in TEST_LEVELS:
        hero = get_hero_base_stats(level)

        monster = scale_monster_stats(
            base_hp=100,
            base_attack=12,
            base_magic_power=10,
            base_defense=8,
            base_magic_defense=6,
            base_speed=10,
            base_accuracy=10,
            base_luck=5,
            base_critical=5,
            level=level,
            power_multiplier=1.0,
        )

        player_damage = calculate_damage(
            attack=hero.attack,
            defense=monster.defense,
            randomize=False,
        )

        monster_damage = calculate_damage(
            attack=monster.attack,
            defense=hero.defense,
            randomize=False,
        )

        print(
            f"Lv.{level:3} | "
            f"Hero ATK={hero.attack:3} → "
            f"Monster DEF={monster.defense:3} | "
            f"Damage={player_damage.damage:3} | "
            f"Monster ATK={monster.attack:3} → "
            f"Hero DEF={hero.defense:3} | "
            f"Damage={monster_damage.damage:3}"
        )

        assert player_damage.damage >= 1, (
            "Player damage below minimum."
        )

        assert monster_damage.damage >= 1, (
            "Monster damage below minimum."
        )


def test_damage_balance() -> None:
    _run_damage_balance()


def _run_damage_growth() -> None:
    print("\n" + "=" * 80)
    print("🧪 DAMAGE GROWTH CHECK")
    print("=" * 80)

    previous_damage = 0

    for level in TEST_LEVELS:
        hero = get_hero_base_stats(level)

        monster = scale_monster_stats(
            base_hp=100,
            base_attack=12,
            base_magic_power=10,
            base_defense=8,
            base_magic_defense=6,
            base_speed=10,
            base_accuracy=10,
            base_luck=5,
            base_critical=5,
            level=level,
            power_multiplier=1.0,
        )

        result = calculate_damage(
            attack=hero.attack,
            defense=monster.defense,
            randomize=False,
        )

        print(
            f"Lv.{level:3} | "
            f"Hero ATK={hero.attack:3} | "
            f"Monster DEF={monster.defense:3} | "
            f"Damage={result.damage:3}"
        )

        assert result.damage >= previous_damage, (
            f"Damage decreased: "
            f"{previous_damage} → {result.damage}"
        )

        previous_damage = result.damage


def test_damage_growth() -> None:
    _run_damage_growth()


def _run_critical_balance() -> None:
    print("\n" + "=" * 80)
    print("🧪 CRITICAL DAMAGE BALANCE")
    print("=" * 80)

    for level in TEST_LEVELS:
        hero = get_hero_base_stats(level)

        monster = scale_monster_stats(
            base_hp=100,
            base_attack=12,
            base_magic_power=10,
            base_defense=8,
            base_magic_defense=6,
            base_speed=10,
            base_accuracy=10,
            base_luck=5,
            base_critical=5,
            level=level,
            power_multiplier=1.0,
        )

        normal = calculate_damage(
            attack=hero.attack,
            defense=monster.defense,
            critical=False,
            randomize=False,
        )

        critical = calculate_damage(
            attack=hero.attack,
            defense=monster.defense,
            critical=True,
            randomize=False,
        )

        ratio = (
            critical.damage / normal.damage
            if normal.damage > 0
            else 0
        )

        print(
            f"Lv.{level:3} | "
            f"Normal={normal.damage:3} | "
            f"Critical={critical.damage:3} | "
            f"Ratio={ratio:.2f}x"
        )

        assert critical.damage > normal.damage, (
            "Critical damage is not higher."
        )


def test_critical_balance() -> None:
    _run_critical_balance()


def _run_element_balance() -> None:
    print("\n" + "=" * 80)
    print("🧪 ELEMENT BALANCE")
    print("=" * 80)

    tests = [
        ("fire", "ice", 1.50),
        ("fire", "fire", 0.75),
        ("fire", "water", 0.70),
        ("water", "fire", 1.50),
        ("ice", "fire", 1.50),
        ("electro", "water", 1.50),
        ("earth", "electro", 1.50),
        ("wind", "earth", 1.50),
        ("shadow", "light", 1.50),
        ("light", "shadow", 1.50),
        ("blood", "shadow", 1.25),
        ("steel", "fire", 0.80),
    ]

    for attack_element, defender_element, expected in tests:
        result = calculate_damage(
            attack=100,
            defense=0,
            attack_element=attack_element,
            defender_element=defender_element,
            randomize=False,
        )

        actual = result.element_multiplier

        print(
            f"{attack_element:8} → "
            f"{defender_element:8} | "
            f"Expected={expected:.2f} | "
            f"Actual={actual:.2f}"
        )

        assert actual == expected, (
            f"Element multiplier mismatch: "
            f"{attack_element} → {defender_element} | "
            f"expected={expected:.2f}, actual={actual:.2f}"
        )

        print("✅")


def test_element_balance() -> None:
    _run_element_balance()


async def main() -> None:
    print("=" * 80)
    print(
        "WORLD ELDORIA - LEVEL SCALING & "
        "COMBAT BALANCE TEST"
    )
    print("=" * 80)

    tests = [
        ("Hero Scaling", _run_hero_scaling),
        ("Monster Scaling", _run_monster_scaling),
        ("Damage Balance", _run_damage_balance),
        ("Damage Growth", _run_damage_growth),
        ("Critical Balance", _run_critical_balance),
        ("Element Balance", _run_element_balance),
    ]

    results = []

    for name, test_function in tests:
        try:
            result = test_function()

            if asyncio.iscoroutine(result):
                await result

            results.append((name, True))

        except AssertionError as exc:
            print(f"❌ {name} FAILED: {exc}")
            results.append((name, False))

        except Exception as exc:
            print(
                f"❌ {name} ERROR: "
                f"{type(exc).__name__}: {exc}"
            )
            results.append((name, False))

    print("\n" + "=" * 80)
    print("📊 FINAL RESULT")
    print("=" * 80)

    all_passed = True

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {name}")

        if not passed:
            all_passed = False

    print("-" * 80)

    if all_passed:
        print(
            "✅ LEVEL SCALING & COMBAT BALANCE "
            "TEST COMPLETED"
        )
        print("✅ No database values were modified.")
    else:
        print(
            "❌ LEVEL SCALING & COMBAT BALANCE "
            "TEST FAILED"
        )

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())