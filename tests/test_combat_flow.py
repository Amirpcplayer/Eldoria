import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.adventure import AdventureEnemy

from services.combat_service import (
    create_battle,
    get_battle,
    player_attack,
    player_defend,
    enemy_turn,
    finish_battle,
)


async def main() -> None:
    print("=" * 80)
    print("WORLD ELDORIA - COMBAT FLOW TEST")
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
            .order_by(
                AdventureEnemy.id
            )
        )

    if character is None:
        print("❌ هیچ Characterای پیدا نشد.")
        return

    if enemy is None:
        print("❌ هیچ AdventureEnemyای پیدا نشد.")
        return

    print()
    print("👤 PLAYER")
    print("-" * 80)
    print(f"Name={character.name}")
    print(f"Level={character.level}")

    print()
    print("👹 ENEMY")
    print("-" * 80)
    print(f"Name={enemy.name}")
    print(f"Enemy ID={enemy.id}")
    print(f"Monster ID={enemy.monster_id}")

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
        print("❌ ساخت Battle شکست خورد.")
        return

    battle_id = battle["battle_id"]

    print()
    print(
        f"Battle ID={battle_id}"
    )

    print(
        f"Player HP="
        f"{battle['player_hp']}/"
        f"{battle['player_max_hp']}"
    )

    print(
        f"Enemy HP="
        f"{battle['enemy_hp']}/"
        f"{battle['enemy_max_hp']}"
    )

    # ------------------------------------------------------------------
    # ATTACK
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print("⚔️ PLAYER ATTACK TEST")
    print("=" * 80)

    old_enemy_hp = battle["enemy_hp"]

    success, damage, victory, battle = await player_attack(
        battle_id
    )

    print(f"Success={success}")
    print(f"Damage={damage}")
    print(f"Victory={victory}")

    if not success or battle is None:
        print("❌ Player attack failed.")
        await finish_battle(battle_id)
        return

    print(
        f"Enemy HP: "
        f"{old_enemy_hp} -> {battle['enemy_hp']}"
    )

    expected_enemy_hp = max(
        0,
        old_enemy_hp - damage,
    )

    if battle["enemy_hp"] != expected_enemy_hp:
        print(
            "❌ Enemy HP calculation mismatch."
        )
        await finish_battle(battle_id)
        return

    print(
        "✅ Player attack damage applied correctly."
    )

    if victory:
        print(
            "⚠️ Enemy died from the first attack."
        )
        await finish_battle(battle_id)
        print()
        print("=" * 80)
        print("⚠️ COMBAT FLOW TEST ENDED EARLY")
        print("=" * 80)
        return

    # ------------------------------------------------------------------
    # ENEMY TURN
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print("👹 ENEMY TURN TEST")
    print("=" * 80)

    old_player_hp = battle["player_hp"]

    success, enemy_damage, defeated, battle = await enemy_turn(
        battle_id
    )

    print(f"Success={success}")
    print(f"Enemy Damage={enemy_damage}")
    print(f"Player Defeated={defeated}")

    if not success or battle is None:
        print("❌ Enemy turn failed.")
        await finish_battle(battle_id)
        return

    print(
        f"Player HP: "
        f"{old_player_hp} -> {battle['player_hp']}"
    )

    expected_player_hp = max(
        0,
        old_player_hp - enemy_damage,
    )

    if battle["player_hp"] != expected_player_hp:
        print(
            "❌ Player HP calculation mismatch."
        )
        await finish_battle(battle_id)
        return

    print(
        "✅ Enemy damage applied correctly."
    )

    if defeated:
        print(
            "⚠️ Player was defeated."
        )
        await finish_battle(battle_id)
        print()
        print("=" * 80)
        print("⚠️ COMBAT FLOW TEST ENDED")
        print("=" * 80)
        return

    # ------------------------------------------------------------------
    # DEFEND
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print("🛡️ DEFEND TEST")
    print("=" * 80)

    success, battle = await player_defend(
        battle_id
    )

    print(f"Success={success}")

    if not success or battle is None:
        print("❌ Player defend failed.")
        await finish_battle(battle_id)
        return

    print(
        f"Defending={battle['defending']}"
    )

    if battle["defending"] is not True:
        print(
            "❌ Defending state was not enabled."
        )
        await finish_battle(battle_id)
        return

    print(
        "✅ Defending state enabled."
    )

    # ------------------------------------------------------------------
    # ENEMY TURN WHILE DEFENDING
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print("🛡️ DEFENSE DAMAGE TEST")
    print("=" * 80)

    old_player_hp = battle["player_hp"]
    normal_defense = battle["player_defense"]

    success, defended_damage, defeated, battle = await enemy_turn(
        battle_id
    )

    print(f"Success={success}")
    print(f"Normal Defense={normal_defense}")
    print(f"Defense Multiplier=1.5x")
    print(f"Damage While Defending={defended_damage}")
    print(f"Player Defeated={defeated}")

    if not success or battle is None:
        print("❌ Enemy turn during defense failed.")
        await finish_battle(battle_id)
        return

    print(
        f"Player HP: "
        f"{old_player_hp} -> {battle['player_hp']}"
    )

    expected_player_hp = max(
        0,
        old_player_hp - defended_damage,
    )

    if battle["player_hp"] != expected_player_hp:
        print(
            "❌ Defend damage calculation mismatch."
        )
        await finish_battle(battle_id)
        return

    if battle["defending"] is not False:
        print(
            "❌ Defending state was not cleared."
        )
        await finish_battle(battle_id)
        return

    print(
        "✅ Defense damage applied correctly."
    )

    print(
        "✅ Defending state cleared after enemy turn."
    )

    # ------------------------------------------------------------------
    # REDIS CHECK
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print("🔄 REDIS STATE TEST")
    print("=" * 80)

    loaded_battle = await get_battle(
        battle_id
    )

    if loaded_battle is None:
        print(
            "❌ Battle could not be loaded from Redis."
        )
        await finish_battle(battle_id)
        return

    print(
        "✅ Battle successfully loaded from Redis."
    )

    print(
        f"Redis Player HP="
        f"{loaded_battle['player_hp']}"
    )

    print(
        f"Redis Enemy HP="
        f"{loaded_battle['enemy_hp']}"
    )

    print(
        f"Redis Defending="
        f"{loaded_battle['defending']}"
    )

    # ------------------------------------------------------------------
    # CLEANUP
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print("🧹 CLEANUP")
    print("=" * 80)

    await finish_battle(
        battle_id
    )

    remaining_battle = await get_battle(
        battle_id
    )

    if remaining_battle is not None:
        print(
            "❌ Battle was not removed from Redis."
        )
        return

    print(
        "✅ Test battle removed from Redis."
    )

    print()
    print("=" * 80)
    print("✅ COMBAT FLOW TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())