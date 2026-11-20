import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character

from services.combat_service import (
    create_battle,
    get_battle,
    get_character_skills,
    player_attack,
    player_skill,
    player_defend,
    enemy_turn,
    flee_battle,
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

    enemy_id = 1

    print("=" * 100)
    print("WORLD ELDORIA - COMBAT ACTIONS TEST")
    print("=" * 100)

    print(
        f"👤 Character: {character.name} | "
        f"Level={character.level} | Character ID={character.id}"
    )
    print("-" * 100)

    # ================================================================
    # 1. CREATE BATTLE
    # ================================================================

    success, message, battle = await create_battle(
        character.telegram_id,
        enemy_id,
    )

    print("1️⃣ CREATE BATTLE")
    print(f"Success: {success}")
    print(f"Message: {message}")

    if not success or battle is None:
        print("❌ Could not create battle")
        print("=" * 100)
        return

    battle_id = battle["battle_id"]

    print(f"Battle ID: {battle_id}")
    print(
        f"Player HP: "
        f"{battle['player_hp']}/{battle['player_max_hp']}"
    )
    print(
        f"Player Mana: "
        f"{battle['player_mana']}/{battle['player_max_mana']}"
    )
    print(
        f"Enemy HP: "
        f"{battle['enemy_hp']}/{battle['enemy_max_hp']}"
    )
    print("-" * 100)

    # ================================================================
    # 2. PLAYER ATTACK
    # ================================================================

    print("2️⃣ PLAYER ATTACK")

    old_enemy_hp = battle["enemy_hp"]

    success, damage, victory, battle = await player_attack(
        battle_id
    )

    print(f"Success: {success}")
    print(f"Damage: {damage}")
    print(f"Victory: {victory}")

    if not success or battle is None:
        print("❌ Player attack failed")
        await flee_battle(battle_id)
        print("=" * 100)
        return

    print(
        f"Enemy HP: {old_enemy_hp} → "
        f"{battle['enemy_hp']}/{battle['enemy_max_hp']}"
    )

    if battle["enemy_hp"] > old_enemy_hp:
        print("❌ Enemy HP increased after attack")
        await flee_battle(battle_id)
        print("=" * 100)
        return

    print("✅ Attack action works")
    print("-" * 100)

    # ================================================================
    # 3. ENEMY TURN
    # ================================================================

    print("3️⃣ ENEMY TURN")

    old_player_hp = battle["player_hp"]

    success, damage, defeated, battle = await enemy_turn(
        battle_id
    )

    print(f"Success: {success}")
    print(f"Damage: {damage}")
    print(f"Defeated: {defeated}")

    if not success or battle is None:
        print("❌ Enemy turn failed")
        await flee_battle(battle_id)
        print("=" * 100)
        return

    print(
        f"Player HP: {old_player_hp} → "
        f"{battle['player_hp']}/{battle['player_max_hp']}"
    )

    if battle["player_hp"] > old_player_hp:
        print("❌ Player HP increased unexpectedly")
        await flee_battle(battle_id)
        print("=" * 100)
        return

    print("✅ Enemy turn works")
    print("-" * 100)

    # ================================================================
    # 4. PLAYER DEFEND
    # ================================================================

    print("4️⃣ PLAYER DEFEND")

    old_player_hp = battle["player_hp"]

    success, battle = await player_defend(
        battle_id
    )

    print(f"Success: {success}")

    if not success or battle is None:
        print("❌ Defend action failed")
        await flee_battle(battle_id)
        print("=" * 100)
        return

    print(
        f"Player HP: {old_player_hp} → "
        f"{battle['player_hp']}/{battle['player_max_hp']}"
    )

    print(
        f"Defending state: "
        f"{battle.get('defending')}"
    )

    if not battle.get("defending"):
        print("❌ Player defending state was not enabled")
        await flee_battle(battle_id)
        print("=" * 100)
        return

    print("✅ Defend action works")
    print("-" * 100)

    # ================================================================
    # 5. PLAYER SKILL
    # ================================================================

    print("5️⃣ PLAYER SKILL")

    skills = await get_character_skills(
        character.id
    )

    if not skills:
        print("⚠️ No learned skills found")
        print("⚠️ Skill action skipped")

    else:
        skill, character_skill = skills[0]

        print(
            f"Skill: {skill.name} | "
            f"Skill ID={skill.id} | "
            f"Level={character_skill.level}"
        )

        current_mana = battle["player_mana"]
        old_enemy_hp = battle["enemy_hp"]

        success, message, damage, victory, battle = await player_skill(
            battle_id,
            skill.id,
        )

        print(f"Success: {success}")
        print(f"Message: {message}")
        print(f"Damage: {damage}")
        print(f"Victory: {victory}")

        if not success:
            print("⚠️ Skill could not be used")

        elif battle is None:
            print("❌ Skill returned no battle state")
            print("=" * 100)
            return

        else:
            print(
                f"Enemy HP: {old_enemy_hp} → "
                f"{battle['enemy_hp']}/{battle['enemy_max_hp']}"
            )

            print(
                f"Mana: {current_mana} → "
                f"{battle['player_mana']}"
            )

            if battle["player_mana"] > current_mana:
                print("❌ Mana increased after skill")
                await flee_battle(battle_id)
                print("=" * 100)
                return

            if battle["enemy_hp"] > old_enemy_hp:
                print("❌ Enemy HP increased after skill")
                await flee_battle(battle_id)
                print("=" * 100)
                return

            print("✅ Skill action works")

    print("-" * 100)

    # ================================================================
    # 6. REDIS BATTLE RESTORE
    # ================================================================

    print("6️⃣ REDIS BATTLE RESTORE")

    restored_battle = await get_battle(
        battle_id
    )

    if restored_battle is None:
        print("❌ Battle could not be restored")
        print("=" * 100)
        return

    print("✅ Battle restored successfully")

    print(
        f"Battle ID: "
        f"{restored_battle.get('battle_id')}"
    )

    print(
        f"Character ID: "
        f"{restored_battle.get('character_id')}"
    )

    print(
        f"Player HP: "
        f"{restored_battle.get('player_hp')}"
    )

    print(
        f"Player Mana: "
        f"{restored_battle.get('player_mana')}"
    )

    print(
        f"Enemy HP: "
        f"{restored_battle.get('enemy_hp')}"
    )

    print(
        f"Defending: "
        f"{restored_battle.get('defending')}"
    )

    print("-" * 100)

    # ================================================================
    # 7. CLEANUP
    # ================================================================

    print("7️⃣ CLEANUP")

    cleanup_success = await flee_battle(
        battle_id
    )

    print(
        f"Cleanup success: "
        f"{cleanup_success}"
    )

    if not cleanup_success:
        print("❌ Cleanup failed")
        print("=" * 100)
        return

    print("✅ Cleanup completed")

    print("=" * 100)
    print("✅ COMBAT ACTIONS TEST COMPLETED")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())