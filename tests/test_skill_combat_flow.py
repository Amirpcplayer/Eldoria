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
    player_skill,
    enemy_turn,
    finish_victory,
    finish_battle,
)


async def main() -> None:
    print("=" * 80)
    print("WORLD ELDORIA - SKILL COMBAT FLOW TEST")
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

    if not skills:
        print("❌ هیچ Skill فعال و Unlock شده‌ای پیدا نشد.")
        return

    skill, character_skill = skills[0]

    print()
    print("👤 PLAYER")
    print("-" * 80)
    print(f"Name={character.name}")
    print(f"Level={character.level}")

    print()
    print("🔮 SKILL")
    print("-" * 80)
    print(f"Name={skill.name}")
    print(f"Skill ID={skill.id}")
    print(f"Skill Level={character_skill.level}")
    print(f"Element={skill.element}")

    print()
    print("👹 ENEMY")
    print("-" * 80)
    print(f"Name={enemy.name}")
    print(f"Enemy ID={enemy.id}")

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

    print(f"Battle ID={battle_id}")
    print(f"Player HP={battle['player_hp']}/{battle['player_max_hp']}")
    print(f"Player Mana={battle['player_mana']}/{battle['player_max_mana']}")
    print(f"Player Magic Power={battle['player_magic_power']}")
    print(f"Enemy HP={battle['enemy_hp']}/{battle['enemy_max_hp']}")
    print(f"Enemy MDEF={battle['enemy_magic_defense']}")

    print()
    print("=" * 80)
    print("🔮 PLAYER USES SKILL")
    print("=" * 80)

    old_enemy_hp = battle["enemy_hp"]
    old_player_mana = battle["player_mana"]

    success, skill_message, damage, victory, battle = await player_skill(
        battle_id,
        skill.id,
    )

    print(f"Success={success}")
    print(f"Message={skill_message}")
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
        f"Player Mana: "
        f"{old_player_mana} -> "
        f"{battle['player_mana']}"
    )

    if victory:
        print()
        print("🏆 Skill defeated the enemy immediately.")

        print()
        print("=" * 80)
        print("🎁 VICTORY REWARD")
        print("=" * 80)

        reward_result = await finish_victory(battle_id)

        print(f"Reward Result={reward_result}")

        if not reward_result[0]:
            print("❌ Victory reward failed.")
            return

        _, xp, skill_xp, gold, levels_gained = reward_result

        print(f"✨ XP={xp}")
        print(f"🔮 Skill XP={skill_xp}")
        print(f"💰 Gold={gold}")
        print(f"🎉 Levels Gained={levels_gained}")

    else:
        print()
        print("=" * 80)
        print("👹 ENEMY TURN")
        print("=" * 80)

        enemy_success, enemy_damage, defeated, battle = await enemy_turn(
            battle_id
        )

        print(f"Success={enemy_success}")
        print(f"Enemy Damage={enemy_damage}")
        print(f"Player Defeated={defeated}")

        if not enemy_success or battle is None:
            print("❌ Enemy turn failed.")
            await finish_battle(battle_id)
            return

        print(
            f"Player HP after enemy turn="
            f"{battle['player_hp']}/{battle['player_max_hp']}"
        )

        if defeated:
            print()
            print("💀 Player was defeated.")

            await finish_battle(battle_id)

            print("✅ Defeat battle cleanup completed.")
            return

        print()
        print("✅ Enemy turn completed successfully.")

        print()
        print("=" * 80)
        print("🔄 REDIS VERIFICATION")
        print("=" * 80)

        loaded_battle = await get_battle(battle_id)

        if loaded_battle is None:
            print("❌ Battle could not be loaded from Redis.")
            return

        print("✅ Battle successfully loaded from Redis.")
        print(
            f"Redis Player HP="
            f"{loaded_battle['player_hp']}"
        )
        print(
            f"Redis Enemy HP="
            f"{loaded_battle['enemy_hp']}"
        )
        print(
            f"Redis Player Mana="
            f"{loaded_battle['player_mana']}"
        )

        await finish_battle(battle_id)

        print()
        print("🧹 Battle cleanup completed.")

    print()
    print("=" * 80)
    print("✅ SKILL COMBAT FLOW TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())