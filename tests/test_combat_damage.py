import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.adventure import AdventureEnemy
from models.monster import Monster

from services.character_stats_service import (
    calculate_character_combat_stats,
)
from services.monster_level_service import (
    calculate_monster_level,
)
from services.monster_stats_service import (
    calculate_monster_stats,
)
from services.damage_service import (
    calculate_damage,
)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character)
            .order_by(Character.id)
        )

        enemy_result = await session.execute(
            select(
                AdventureEnemy,
                Monster,
            )
            .join(
                Monster,
                AdventureEnemy.monster_id == Monster.id,
            )
            .order_by(
                AdventureEnemy.id,
            )
            .limit(3)
        )

        enemies = enemy_result.all()

    print("=" * 80)
    print("WORLD ELDORIA - COMBAT DAMAGE TEST")
    print("=" * 80)

    if character is None:
        print("❌ هیچ Characterای در دیتابیس وجود ندارد.")
        return

    if not enemies:
        print("❌ هیچ Monster متصل به AdventureEnemy پیدا نشد.")
        return

    player_stats = await calculate_character_combat_stats(
        character
    )

    print()
    print("👤 PLAYER")
    print("-" * 80)

    print(
        f"Name={character.name} | "
        f"Level={character.level}"
    )

    print(
        f"❤️ HP={player_stats.hp}/{player_stats.max_hp}"
    )

    print(
        f"⚔️ ATK={player_stats.attack}"
    )

    print(
        f"🛡️ DEF={player_stats.defense}"
    )

    print(
        f"🔮 Magic Power={player_stats.magic_power}"
    )

    print(
        f"🔮 MDEF={player_stats.magic_defense}"
    )

    print()
    print("=" * 80)
    print("⚔️ PLAYER → MONSTER DAMAGE")
    print("=" * 80)

    for enemy, monster in enemies:
        effective_level = calculate_monster_level(
            character_level=character.level,
            enemy_level=enemy.level,
            area_min_level=1,
            area_max_level=100,
        )

        monster_stats = calculate_monster_stats(
            monster=monster,
            level=effective_level,
        )

        result = calculate_damage(
            attack=player_stats.attack,
            defense=monster_stats.defense,
            skill_power=1.0,
            attack_element="neutral",
            defender_element=monster.element,
            resistance=0.0,
            critical=False,
            randomize=False,
        )

        print()
        print(
            f"👹 {monster.name} "
            f"| Lv.{effective_level}"
        )

        print(
            f"Player ATK={player_stats.attack} | "
            f"Monster DEF={monster_stats.defense}"
        )

        print(
            f"⚔️ Damage={result.damage}"
        )

        print(
            f"Defense Multiplier="
            f"{result.defense_multiplier:.3f}"
        )

    print()
    print("=" * 80)
    print("👹 MONSTER → PLAYER DAMAGE")
    print("=" * 80)

    for enemy, monster in enemies:
        effective_level = calculate_monster_level(
            character_level=character.level,
            enemy_level=enemy.level,
            area_min_level=1,
            area_max_level=100,
        )

        monster_stats = calculate_monster_stats(
            monster=monster,
            level=effective_level,
        )

        result = calculate_damage(
            attack=monster_stats.attack,
            defense=player_stats.defense,
            skill_power=1.0,
            attack_element=monster.element,
            defender_element="neutral",
            resistance=0.0,
            critical=False,
            randomize=False,
        )

        print()
        print(
            f"👹 {monster.name} "
            f"| Lv.{effective_level}"
        )

        print(
            f"Monster ATK={monster_stats.attack} | "
            f"Player DEF={player_stats.defense}"
        )

        print(
            f"💥 Damage={result.damage}"
        )

        print(
            f"Defense Multiplier="
            f"{result.defense_multiplier:.3f}"
        )

    print()
    print("=" * 80)
    print("🎯 CRITICAL TEST")
    print("=" * 80)

    normal = calculate_damage(
        attack=player_stats.attack,
        defense=player_stats.defense,
        skill_power=1.0,
        attack_element="neutral",
        defender_element="neutral",
        resistance=0.0,
        critical=False,
        randomize=False,
    )

    critical = calculate_damage(
        attack=player_stats.attack,
        defense=player_stats.defense,
        skill_power=1.0,
        attack_element="neutral",
        defender_element="neutral",
        resistance=0.0,
        critical=True,
        randomize=False,
    )

    print(
        f"Normal Damage={normal.damage}"
    )

    print(
        f"Critical Damage={critical.damage}"
    )

    print(
        f"Critical Multiplier="
        f"{critical.damage / normal.damage:.2f}x"
    )

    print()
    print("=" * 80)
    print("🎲 RANDOM DAMAGE TEST")
    print("=" * 80)

    random_values = []

    for _ in range(10):
        result = calculate_damage(
            attack=player_stats.attack,
            defense=player_stats.defense,
            skill_power=1.0,
            attack_element="neutral",
            defender_element="neutral",
            resistance=0.0,
            critical=False,
            randomize=True,
        )

        random_values.append(result.damage)

    print(
        "Damage Samples="
        + ", ".join(str(value) for value in random_values)
    )

    print(
        f"Minimum={min(random_values)} | "
        f"Maximum={max(random_values)}"
    )

    print()
    print("=" * 80)
    print("🔥 ELEMENT TEST")
    print("=" * 80)

    fire_vs_neutral = calculate_damage(
        attack=20,
        defense=10,
        skill_power=1.0,
        attack_element="fire",
        defender_element="neutral",
        resistance=0.0,
        critical=False,
        randomize=False,
    )

    fire_vs_ice = calculate_damage(
        attack=20,
        defense=10,
        skill_power=1.0,
        attack_element="fire",
        defender_element="ice",
        resistance=0.0,
        critical=False,
        randomize=False,
    )

    fire_vs_fire = calculate_damage(
        attack=20,
        defense=10,
        skill_power=1.0,
        attack_element="fire",
        defender_element="fire",
        resistance=0.0,
        critical=False,
        randomize=False,
    )

    print(
        f"🔥 Fire → Neutral = "
        f"{fire_vs_neutral.damage}"
    )

    print(
        f"🔥 Fire → ❄️ Ice = "
        f"{fire_vs_ice.damage}"
    )

    print(
        f"🔥 Fire → 🔥 Fire = "
        f"{fire_vs_fire.damage}"
    )

    print()
    print("=" * 80)
    print("🛡️ RESISTANCE TEST")
    print("=" * 80)

    no_resistance = calculate_damage(
        attack=20,
        defense=10,
        skill_power=1.0,
        attack_element="fire",
        defender_element="neutral",
        resistance=0.0,
        critical=False,
        randomize=False,
    )

    resistance_20 = calculate_damage(
        attack=20,
        defense=10,
        skill_power=1.0,
        attack_element="fire",
        defender_element="neutral",
        resistance=0.20,
        critical=False,
        randomize=False,
    )

    weakness_25 = calculate_damage(
        attack=20,
        defense=10,
        skill_power=1.0,
        attack_element="fire",
        defender_element="neutral",
        resistance=-0.25,
        critical=False,
        randomize=False,
    )

    print(
        f"0% Resistance = "
        f"{no_resistance.damage}"
    )

    print(
        f"20% Resistance = "
        f"{resistance_20.damage}"
    )

    print(
        f"25% Weakness = "
        f"{weakness_25.damage}"
    )

    print()
    print("=" * 80)
    print("✅ COMBAT DAMAGE TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())