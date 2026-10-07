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

from services.power_service import (
    get_hero_base_stats,
    scale_monster_stats,
)

from services.damage_service import calculate_damage


# ------------------------------------------------------------------
# TEST LEVELS
# ------------------------------------------------------------------
TEST_LEVELS = [1, 5, 10, 20, 50, 100]


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def print_separator():
    print("-" * 80)


def validate_positive(name: str, value: int) -> bool:
    if value <= 0:
        print(f"❌ {name} invalid: {value}")
        return False

    print(f"✅ {name}: {value}")
    return True


# ------------------------------------------------------------------
# HERO SCALING
# ------------------------------------------------------------------
def test_hero_scaling() -> bool:
    print("\n" + "=" * 80)
    print("🧪 HERO LEVEL SCALING")
    print("=" * 80)

    passed = True
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

        if any(value <= 0 for value in values):
            print(f"❌ Invalid stat at Level {level}")
            passed = False

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
                [
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
                ],
            ):
                if new < old:
                    print(
                        f"❌ {stat_name} decreased: "
                        f"{old} → {new}"
                    )
                    passed = False

        previous = stats

    return passed


# ------------------------------------------------------------------
# MONSTER SCALING
# ------------------------------------------------------------------
async def test_monster_scaling() -> bool:
    print("\n" + "=" * 80)
    print("🧪 MONSTER LEVEL SCALING")
    print("=" * 80)

    passed = True

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Monster)
            .where(Monster.is_active.is_(True))
            .order_by(Monster.id)
        )

        monsters = list(result.scalars().all())

    print(f"Active Monsters={len(monsters)}")

    if not monsters:
        print("❌ No active monsters found.")
        return False

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

            if stats.hp < previous_hp:
                print("❌ HP decreased.")
                passed = False

            if stats.attack < previous_attack:
                print("❌ Attack decreased.")
                passed = False

            if stats.defense < previous_defense:
                print("❌ Defense decreased.")
                passed = False

            previous_hp = stats.hp
            previous_attack = stats.attack
            previous_defense = stats.defense

    return passed


# ------------------------------------------------------------------
# DAMAGE BALANCE
# ------------------------------------------------------------------
def test_damage_balance() -> bool:
    print("\n" + "=" * 80)
    print("🧪 DAMAGE BALANCE")
    print("=" * 80)

    passed = True

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

        if player_damage.damage < 1:
            print("❌ Player damage below minimum.")
            passed = False

        if monster_damage.damage < 1:
            print("❌ Monster damage below minimum.")
            passed = False

    return passed


# ------------------------------------------------------------------
# DAMAGE GROWTH
# ------------------------------------------------------------------
def test_damage_growth() -> bool:
    print("\n" + "=" * 80)
    print("🧪 DAMAGE GROWTH CHECK")
    print("=" * 80)

    passed = True

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

        if result.damage < previous_damage:
            print(
                f"❌ Damage decreased: "
                f"{previous_damage} → {result.damage}"
            )
            passed = False

        previous_damage = result.damage

    return passed


# ------------------------------------------------------------------
# CRITICAL BALANCE
# ------------------------------------------------------------------
def test_critical_balance() -> bool:
    print("\n" + "=" * 80)
    print("🧪 CRITICAL DAMAGE BALANCE")
    print("=" * 80)

    passed = True

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

        if critical.damage <= normal.damage:
            print("❌ Critical damage is not higher.")
            passed = False

    return passed


# ------------------------------------------------------------------
# ELEMENT BALANCE
# ------------------------------------------------------------------
def test_element_balance() -> bool:
    print("\n" + "=" * 80)
    print("🧪 ELEMENT BALANCE")
    print("=" * 80)

    passed = True

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

        if actual != expected:
            print("❌ Element multiplier mismatch.")
            passed = False
        else:
            print("✅")

    return passed


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
async def main():
    print("=" * 80)
    print("WORLD ELDORIA - LEVEL SCALING & COMBAT BALANCE TEST")
    print("=" * 80)

    results = []

    results.append(
        ("Hero Scaling", test_hero_scaling())
    )

    results.append(
        ("Monster Scaling", await test_monster_scaling())
    )

    results.append(
        ("Damage Balance", test_damage_balance())
    )

    results.append(
        ("Damage Growth", test_damage_growth())
    )

    results.append(
        ("Critical Balance", test_critical_balance())
    )

    results.append(
        ("Element Balance", test_element_balance())
    )

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
        print("✅ LEVEL SCALING & COMBAT BALANCE TEST COMPLETED")
        print("✅ No database values were modified.")
    else:
        print("❌ LEVEL SCALING & COMBAT BALANCE TEST FAILED")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())