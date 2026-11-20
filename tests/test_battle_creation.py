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
    finish_battle,
)


async def main() -> None:
    print("=" * 80)
    print("WORLD ELDORIA - BATTLE CREATION TEST")
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

    print(
        f"Name={character.name}"
    )

    print(
        f"Level={character.level}"
    )

    print()
    print("👹 ENEMY")
    print("-" * 80)

    print(
        f"Name={enemy.name}"
    )

    print(
        f"Enemy ID={enemy.id}"
    )

    print(
        f"Monster ID={enemy.monster_id}"
    )

    print()
    print("=" * 80)
    print("⚔️ CREATING BATTLE")
    print("=" * 80)

    success, message, battle = await create_battle(
        character.telegram_id,
        enemy.id,
    )

    print()
    print(
        f"Success={success}"
    )

    print(
        f"Message={message}"
    )

    if not success or battle is None:
        print()
        print("❌ Battle ساخته نشد.")
        return

    print()
    print("⚔️ BATTLE DATA")
    print("-" * 80)

    print(
        f"Battle ID={battle['battle_id']}"
    )

    print(
        f"Enemy={battle['enemy_name']}"
    )

    print(
        f"Enemy Level={battle['enemy_level']}"
    )

    print(
        f"Enemy Element={battle['enemy_element']}"
    )

    print(
        f"❤️ Enemy HP="
        f"{battle['enemy_hp']}/"
        f"{battle['enemy_max_hp']}"
    )

    print(
        f"⚔️ Enemy ATK="
        f"{battle['enemy_attack']}"
    )

    print(
        f"🛡️ Enemy DEF="
        f"{battle['enemy_defense']}"
    )

    print(
        f"🔮 Enemy MDEF="
        f"{battle['enemy_magic_defense']}"
    )

    print()
    print(
        f"👤 Player Level="
        f"{battle['player_level']}"
    )

    print(
        f"❤️ Player HP="
        f"{battle['player_hp']}/"
        f"{battle['player_max_hp']}"
    )

    print(
        f"⚔️ Player ATK="
        f"{battle['player_attack']}"
    )

    print(
        f"🛡️ Player DEF="
        f"{battle['player_defense']}"
    )

    print(
        f"🔮 Player MDEF="
        f"{battle['player_magic_defense']}"
    )

    print(
        f"🔵 Player Mana="
        f"{battle['player_mana']}/"
        f"{battle['player_max_mana']}"
    )

    print()
    print("🔥 RESISTANCES")
    print("-" * 80)

    print(
        f"Fire={battle['enemy_fire_resistance']}"
    )

    print(
        f"Water={battle['enemy_water_resistance']}"
    )

    print(
        f"Ice={battle['enemy_ice_resistance']}"
    )

    print(
        f"Earth={battle['enemy_earth_resistance']}"
    )

    print(
        f"Wind={battle['enemy_wind_resistance']}"
    )

    print(
        f"Electro={battle['enemy_electro_resistance']}"
    )

    print(
        f"Shadow={battle['enemy_shadow_resistance']}"
    )

    print(
        f"Light={battle['enemy_light_resistance']}"
    )

    print(
        f"Blood={battle['enemy_blood_resistance']}"
    )

    print(
        f"Steel={battle['enemy_steel_resistance']}"
    )

    print()
    print("=" * 80)
    print("🔄 REDIS BATTLE TEST")
    print("=" * 80)

    loaded_battle = await get_battle(
        battle["battle_id"]
    )

    if loaded_battle is None:
        print("❌ Battle از Redis قابل بازیابی نیست.")

        await finish_battle(
            battle["battle_id"]
        )

        return

    print(
        "✅ Battle successfully loaded from Redis."
    )

    print(
        f"Redis Battle ID="
        f"{loaded_battle['battle_id']}"
    )

    print(
        f"Redis Enemy HP="
        f"{loaded_battle['enemy_hp']}"
    )

    print(
        f"Redis Player HP="
        f"{loaded_battle['player_hp']}"
    )

    print()
    print("=" * 80)
    print("🧹 CLEANUP")
    print("=" * 80)

    await finish_battle(
        battle["battle_id"]
    )

    print(
        "✅ Test battle removed from Redis."
    )

    print()
    print("=" * 80)
    print("✅ BATTLE CREATION TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())