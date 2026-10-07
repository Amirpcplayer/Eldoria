import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.adventure import AdventureEnemy
from models.character_skill import CharacterSkill
from models.skill import Skill

from services.combat_service import (
    create_battle,
    get_battle,
    get_character_skill,
    player_skill,
    finish_battle,
)


async def main() -> None:
    print("=" * 80)
    print("WORLD ELDORIA - SKILL BATTLE TEST")
    print("=" * 80)

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character)
            .order_by(Character.id)
        )

        enemy = await session.scalar(
            select(AdventureEnemy)
            .where(
                AdventureEnemy.is_active.is_(True)
            )
            .order_by(AdventureEnemy.id)
        )

        if character is None:
            print("❌ هیچ Characterای پیدا نشد.")
            return

        if enemy is None:
            print("❌ هیچ AdventureEnemyای پیدا نشد.")
            return

        result = await session.execute(
            select(
                Skill,
                CharacterSkill,
            )
            .join(
                CharacterSkill,
                CharacterSkill.skill_id == Skill.id,
            )
            .where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.unlocked.is_(True),
                Skill.is_active.is_(True),
            )
            .order_by(
                CharacterSkill.slot,
                Skill.id,
            )
        )

        skills = list(result.all())

    print()
    print("👤 PLAYER")
    print("-" * 80)
    print(f"Name={character.name}")
    print(f"Level={character.level}")
    print(f"Magic Power={character.magic_power}")
    print(f"Mana={character.mana}/{character.max_mana}")

    if not skills:
        print()
        print("❌ هیچ Skill فعال و Unlock شده‌ای پیدا نشد.")
        return

    print()
    print("🔮 AVAILABLE SKILLS")
    print("-" * 80)

    for skill, character_skill in skills:
        print(
            f"ID={skill.id} | "
            f"Name={skill.name} | "
            f"Level={character_skill.level} | "
            f"Element={skill.element}"
        )

    skill, character_skill = skills[0]

    print()
    print("=" * 80)
    print("🔮 SELECTED SKILL")
    print("=" * 80)

    print(f"Skill={skill.name}")
    print(f"Skill ID={skill.id}")
    print(f"Skill Level={character_skill.level}")
    print(f"Element={skill.element}")

    print()
    print("=" * 80)
    print("⚔️ CREATE BATTLE")
    print("=" * 80)

    success, message, battle = await create_battle(
        character.telegram_id,
        enemy.id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if not success or battle is None:
        return

    battle_id = battle["battle_id"]

    print()
    print(f"Battle ID={battle_id}")
    print(f"Enemy={battle['enemy_name']}")
    print(f"Enemy Level={battle['enemy_level']}")
    print(f"Enemy Element={battle['enemy_element']}")
    print(
        f"Enemy HP="
        f"{battle['enemy_hp']}/"
        f"{battle['enemy_max_hp']}"
    )
    print(
        f"Enemy MDEF="
        f"{battle['enemy_magic_defense']}"
    )

    print()
    print("=" * 80)
    print("🔮 USING SKILL")
    print("=" * 80)

    old_mana = battle["player_mana"]
    old_enemy_hp = battle["enemy_hp"]

    skill_level = character_skill.level

    from services.skill_service import (
        get_skill_mana_cost,
        get_skill_power,
    )

    mana_cost = get_skill_mana_cost(
        skill,
        skill_level,
    )

    skill_power = get_skill_power(
        skill,
        skill_level,
    )

    print(f"Mana Before={old_mana}")
    print(f"Mana Cost={mana_cost}")
    print(f"Skill Power={skill_power}")
    print(f"Skill Multiplier={skill_power / 100:.2f}x")

    success, message, damage, victory, battle = await player_skill(
        battle_id,
        skill.id,
    )

    print()
    print(f"Success={success}")
    print(f"Message={message}")
    print(f"Damage={damage}")
    print(f"Victory={victory}")

    if not success or battle is None:
        print("❌ Skill execution failed.")
        await finish_battle(battle_id)
        return

    print()
    print(
        f"Enemy HP: "
        f"{old_enemy_hp} -> "
        f"{battle['enemy_hp']}"
    )

    print(
        f"Mana: "
        f"{old_mana} -> "
        f"{battle['player_mana']}"
    )

    expected_mana = old_mana - mana_cost

    if battle["player_mana"] != expected_mana:
        print(
            "❌ Mana calculation mismatch."
        )
        await finish_battle(battle_id)
        return

    print(
        "✅ Mana cost applied correctly."
    )

    expected_enemy_hp = max(
        0,
        old_enemy_hp - damage,
    )

    if battle["enemy_hp"] != expected_enemy_hp:
        print(
            "❌ Skill damage calculation mismatch."
        )
        await finish_battle(battle_id)
        return

    print(
        "✅ Skill damage applied correctly."
    )

    print()
    print("=" * 80)
    print("🔄 REDIS VERIFICATION")
    print("=" * 80)

    loaded_battle = await get_battle(
        battle_id
    )

    if loaded_battle is None:
        print(
            "❌ Battle could not be loaded from Redis."
        )
        return

    print(
        "✅ Battle successfully loaded from Redis."
    )

    print(
        f"Redis Enemy HP="
        f"{loaded_battle['enemy_hp']}"
    )

    print(
        f"Redis Player Mana="
        f"{loaded_battle['player_mana']}"
    )

    if victory:
        print()
        print(
            "🏆 Skill defeated the enemy."
        )

    print()
    print("=" * 80)
    print("🧹 CLEANUP")
    print("=" * 80)

    await finish_battle(
        battle_id
    )

    print(
        "✅ Test battle removed from Redis."
    )

    print()
    print("=" * 80)
    print("✅ SKILL BATTLE TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())