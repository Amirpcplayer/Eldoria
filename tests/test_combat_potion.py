import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.inventory import Inventory
from models.item import Item

from services.combat_service import (
    create_battle,
    get_battle,
    get_healing_potions,
    use_healing_potion,
    flee_battle,
)


async def get_first_character() -> Character | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character)
            .order_by(Character.id)
            .limit(1)
        )


async def main() -> None:
    print("=" * 100)
    print("WORLD ELDORIA - COMBAT POTION TEST")
    print("=" * 100)

    character = await get_first_character()

    if character is None:
        print("❌ No character found")
        return

    print(
        f"👤 Character: {character.name} | "
        f"Level={character.level} | "
        f"Character ID={character.id}"
    )

    print("-" * 100)
    print("1️⃣ FIND HEALING POTIONS")

    potions = await get_healing_potions(
        character.id
    )

    if not potions:
        print("❌ No healing potions found in inventory")
        return

    for inventory_item, item, heal_amount in potions:
        print(
            f"🧪 {item.name} | "
            f"Quantity={inventory_item.quantity} | "
            f"Heal={heal_amount}"
        )

    inventory_item, potion, heal_amount = potions[0]

    print("-" * 100)
    print("2️⃣ CREATE BATTLE")

    success, message, battle = await create_battle(
        character.telegram_id,
        1,
    )

    if not success or battle is None:
        print(f"❌ Battle creation failed: {message}")
        return

    battle_id = battle["battle_id"]

    print(f"Success: {success}")
    print(f"Message: {message}")
    print(f"Battle ID: {battle_id}")
    print(
        f"Player HP: "
        f"{battle['player_hp']}/{battle['player_max_hp']}"
    )
    print(
        f"Enemy HP: "
        f"{battle['enemy_hp']}/{battle['enemy_max_hp']}"
    )

    print("-" * 100)
    print("3️⃣ DAMAGE PLAYER BEFORE POTION")

    async with AsyncSessionLocal() as session:
        db_character = await session.scalar(
            select(Character)
            .where(Character.id == character.id)
        )

        if db_character is None:
            print("❌ Character not found")
            return

    battle = await get_battle(
        battle_id
    )

    if battle is None:
        print("❌ Battle not found")
        return

    original_hp = battle["player_hp"]

    if original_hp == battle["player_max_hp"]:
        damage_amount = min(
            20,
            battle["player_max_hp"] - 1,
        )

        battle["player_hp"] -= damage_amount

        from services.combat_service import save_battle

        await save_battle(
            battle
        )

        battle = await get_battle(
            battle_id
        )

    if battle is None:
        print("❌ Battle disappeared")
        return

    print(
        f"Player HP after damage: "
        f"{battle['player_hp']}/{battle['player_max_hp']}"
    )

    print("-" * 100)
    print("4️⃣ USE HEALING POTION")

    quantity_before = inventory_item.quantity
    hp_before = battle["player_hp"]

    (
        potion_success,
        potion_message,
        actual_heal,
        battle_after_potion,
    ) = await use_healing_potion(
        battle_id,
        potion.id,
    )

    print(f"Success: {potion_success}")
    print(f"Message: {potion_message}")
    print(f"Actual Heal: {actual_heal}")

    if not potion_success or battle_after_potion is None:
        print("❌ Potion use failed")
        await flee_battle(battle_id)
        return

    print(
        f"HP: {hp_before} → "
        f"{battle_after_potion['player_hp']}/"
        f"{battle_after_potion['player_max_hp']}"
    )

    print("-" * 100)
    print("5️⃣ CHECK INVENTORY CONSUMPTION")

    potions_after = await get_healing_potions(
        character.id
    )

    quantity_after = 0

    for inventory_after, item_after, _ in potions_after:
        if item_after.id == potion.id:
            quantity_after = inventory_after.quantity
            break

    print(
        f"Potion quantity: "
        f"{quantity_before} → {quantity_after}"
    )

    if quantity_after == quantity_before - 1:
        print("✅ Potion quantity consumed correctly")
    else:
        print("❌ Potion quantity was not consumed correctly")

    print("-" * 100)
    print("6️⃣ CHECK HP CAP")

    if (
        battle_after_potion["player_hp"]
        <= battle_after_potion["player_max_hp"]
    ):
        print("✅ HP cap works correctly")
    else:
        print("❌ HP exceeded maximum HP")

    print("-" * 100)
    print("7️⃣ CHECK TURN CONSUMPTION")

    print(
        f"Turn after potion: "
        f"{battle_after_potion['turn']}"
    )

    print("-" * 100)
    print("8️⃣ CLEANUP")

    cleanup_success = await flee_battle(
        battle_id
    )

    print(
        f"Cleanup success: {cleanup_success}"
    )

    if cleanup_success:
        print("✅ Cleanup completed")
    else:
        print("⚠️ Cleanup returned False")

    print("=" * 100)
    print("✅ COMBAT POTION TEST COMPLETED")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())