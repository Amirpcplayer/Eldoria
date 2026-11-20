import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character

from services.adventure_service import (
    get_area,
    get_enemy,
    get_effective_enemy_level,
)
from services.combat_service import (
    create_battle,
    get_battle,
)


async def get_first_character() -> Character | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character).order_by(Character.id)
        )


async def main():
    character = await get_first_character()

    if character is None:
        print("❌ No character found")
        return

    area = await get_area(1)

    if area is None:
        print("❌ Area not found")
        return

    enemy = await get_enemy(1)

    if enemy is None:
        print("❌ Enemy not found")
        return

    print("=" * 100)
    print("WORLD ELDORIA - ADVENTURE → COMBAT INTEGRATION TEST")
    print("=" * 100)

    print(
        f"👤 Character: {character.name} | "
        f"Level={character.level} | "
        f"Character ID={character.id}"
    )

    print(
        f"📍 Area: {area.name} | "
        f"Level Range={area.min_level}-{area.max_level}"
    )

    print(
        f"👹 Enemy: {enemy.name} | "
        f"Base Level={enemy.level} | "
        f"Monster ID={enemy.monster_id}"
    )

    effective_level = get_effective_enemy_level(
        character,
        enemy,
        area,
    )

    print(f"⚙️ Effective Monster Level={effective_level}")
    print("-" * 100)

    # فقط Telegram ID واقعی شخصیت را از دیتابیس می‌گیریم.
    # هیچ Telegram ID هاردکد نشده است.
    success, message, battle = await create_battle(
        character.telegram_id,
        enemy.id,
    )

    print(f"CREATE BATTLE: success={success}")
    print(f"Message: {message}")

    if not success:
        print("❌ Battle creation failed")
        print("=" * 100)
        return

    if battle is None:
        print("❌ Battle object is None")
        print("=" * 100)
        return

    print()
    print("BATTLE STATE")
    print("-" * 100)

    print(f"Battle ID: {battle.get('battle_id')}")
    print(f"Telegram ID: {battle.get('telegram_id')}")
    print(f"Character ID: {battle.get('character_id')}")
    print(f"Enemy ID: {battle.get('enemy_id')}")
    print(f"Enemy Name: {battle.get('enemy_name')}")
    print(f"Enemy Level: {battle.get('enemy_level')}")
    print(f"Enemy HP: {battle.get('enemy_hp')}/{battle.get('enemy_max_hp')}")
    print(f"Enemy ATK: {battle.get('enemy_attack')}")
    print(f"Enemy Magic: {battle.get('enemy_magic_power')}")
    print(f"Enemy DEF: {battle.get('enemy_defense')}")
    print(f"Enemy MDEF: {battle.get('enemy_magic_defense')}")
    print(f"Enemy SPD: {battle.get('enemy_speed')}")
    print(f"Enemy ACC: {battle.get('enemy_accuracy')}")
    print(f"Enemy LUCK: {battle.get('enemy_luck')}")
    print(f"Enemy CRIT: {battle.get('enemy_critical')}")
    print(f"Enemy Element: {battle.get('enemy_element')}")
    print("-" * 100)

    saved_battle = await get_battle(
        battle["battle_id"]
    )

    if saved_battle is None:
        print("❌ Battle could not be restored from Redis")
        print("=" * 100)
        return

    print("✅ Battle successfully restored from Redis")
    print(f"Restored Battle ID: {saved_battle.get('battle_id')}")

    print("=" * 100)
    print("✅ ADVENTURE → COMBAT INTEGRATION TEST COMPLETED")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
    