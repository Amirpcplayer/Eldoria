from pathlib import Path
import sys
import asyncio


BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character

from services.equipment_service import (
    add_equipment_to_character,
    equip_equipment,
    unequip_equipment,
    get_character_equipments,
    get_equipped_equipments,
    get_equipment_stats,
)


async def get_test_character():
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character)
            .order_by(Character.id)
            .limit(1)
        )


async def main():
    print("========================================")
    print("   World Eldoria - Equipment Actions")
    print("========================================")

    character = await get_test_character()

    if character is None:
        print("❌ No character found.")
        return

    telegram_id = character.telegram_id

    print("\n[1] Test character")
    print(f"✅ Character: {character.name}")
    print(f"   Level: {character.level}")

    print("\n[2] Adding test equipment")

    success, message = await add_equipment_to_character(
        telegram_id=telegram_id,
        equipment_id=1,
        quantity=1,
    )

    if not success:
        print(f"❌ {message}")
        return

    print("✅ Equipment added.")
    print(message.replace("<b>", "").replace("</b>", ""))

    print("\n[3] Checking inventory")

    equipments = await get_character_equipments(
        telegram_id
    )

    found = False

    for character_equipment, equipment in equipments:
        if equipment.id == 1:
            found = True

            print(
                f"✅ Found: {equipment.name}"
            )

            print(
                f"   Quantity: "
                f"{character_equipment.quantity}"
            )

            print(
                f"   Equipped: "
                f"{character_equipment.equipped}"
            )

    if not found:
        print(
            "❌ Equipment was not found "
            "in character inventory."
        )
        return

    print("\n[4] Testing Equip")

    success, message = await equip_equipment(
        telegram_id=telegram_id,
        equipment_id=1,
    )

    if not success:
        print(f"❌ {message}")
        return

    print("✅ Equip successful.")
    print(message.replace("<b>", "").replace("</b>", ""))

    print("\n[5] Checking equipped equipment")

    equipped = await get_equipped_equipments(
        telegram_id
    )

    equipped_found = False

    for character_equipment, equipment in equipped:
        print(
            f"   - {equipment.name} "
            f"[equipped]"
        )

        if equipment.id == 1:
            equipped_found = True

    if not equipped_found:
        print(
            "❌ Test equipment was not equipped."
        )
        return

    print("✅ Equipment is equipped.")

    print("\n[6] Testing equipment stats")

    stats = await get_equipment_stats(
        telegram_id
    )

    print(
        f"   Attack: +{stats['attack']}"
    )

    print(
        f"   Magic Power: +{stats['magic_power']}"
    )

    print(
        f"   Defense: +{stats['defense']}"
    )

    print(
        f"   Magic Defense: +{stats['magic_defense']}"
    )

    print(
        f"   HP: +{stats['hp']}"
    )

    print(
        f"   Mana: +{stats['mana']}"
    )

    print(
        f"   Speed: +{stats['speed']}"
    )

    print(
        f"   Accuracy: +{stats['accuracy']}"
    )

    print(
        f"   Critical: +{stats['critical']}"
    )

    if stats["attack"] < 15:
        print(
            "❌ Equipment stats were not "
            "calculated correctly."
        )
        return

    print("✅ Equipment stats are correct.")

    print("\n[7] Testing Unequip")

    success, message = await unequip_equipment(
        telegram_id=telegram_id,
        equipment_id=1,
    )

    if not success:
        print(f"❌ {message}")
        return

    print("✅ Unequip successful.")
    print(message.replace("<b>", "").replace("</b>", ""))

    print("\n[8] Final equipment state")

    equipped_after = await get_equipped_equipments(
        telegram_id
    )

    still_equipped = any(
        equipment.id == 1
        for _, equipment in equipped_after
    )

    if still_equipped:
        print(
            "❌ Equipment is still equipped."
        )
        return

    print("✅ Equipment is no longer equipped.")

    final_stats = await get_equipment_stats(
        telegram_id
    )

    if any(
        value != 0
        for value in final_stats.values()
    ):
        print(
            "❌ Equipment stats were not "
            "reset after unequip."
        )
        return

    print("✅ Equipment stats returned to zero.")

    print("\n========================================")
    print("✅ ALL EQUIPMENT ACTION TESTS PASSED")
    print("========================================")


if __name__ == "__main__":
    asyncio.run(main())