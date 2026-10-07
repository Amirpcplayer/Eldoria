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
    get_equipment,
    get_equipment_stats,
    get_final_character_stats,
    get_character_equipments,
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
    print("      World Eldoria - Equipment Test")
    print("========================================")

    character = await get_test_character()

    if character is None:
        print("❌ No character found in database.")
        print(
            "ℹ️ Create a character first, "
            "then run the test again."
        )
        return

    test_telegram_id = character.telegram_id

    print("\n[0] Testing character lookup...")
    print(f"✅ Character: {character.name}")
    print(f"   Telegram ID: {test_telegram_id}")
    print(f"   Level: {character.level}")

    print("\n[1] Testing equipment lookup...")

    equipment = await get_equipment(1)

    if equipment is None:
        print("❌ Equipment ID 1 not found.")
        return

    print(
        f"✅ Equipment found: "
        f"{equipment.name}"
    )

    print(
        f"   Type: "
        f"{equipment.equipment_type}"
    )

    print(
        f"   Rarity: "
        f"{equipment.rarity}"
    )

    print(
        f"   Required level: "
        f"{equipment.required_level}"
    )

    print("\n[2] Testing character equipment list...")

    equipments = await get_character_equipments(
        test_telegram_id
    )

    print(
        "✅ Character equipment count: "
        f"{len(equipments)}"
    )

    if equipments:
        for character_equipment, equipment in equipments:
            status = (
                "EQUIPPED"
                if character_equipment.equipped
                else "IN INVENTORY"
            )

            print(
                f"   - {equipment.name} "
                f"x{character_equipment.quantity} "
                f"[{status}]"
            )
    else:
        print(
            "   ℹ️ Character has no equipment yet."
        )

    print("\n[3] Testing equipment stats...")

    equipment_stats = await get_equipment_stats(
        test_telegram_id
    )

    print("✅ Equipment stats:")

    for stat_name, value in equipment_stats.items():
        print(
            f"   {stat_name}: +{value}"
        )

    print("\n[4] Testing final character stats...")

    final_stats = await get_final_character_stats(
        test_telegram_id
    )

    if final_stats is None:
        print("❌ Character not found.")
        return

    print("✅ Final character stats:")

    for stat_name, value in final_stats.items():
        print(
            f"   {stat_name}: {value}"
        )

    print("\n========================================")
    print("✅ Equipment service test completed.")
    print("========================================")


if __name__ == "__main__":
    asyncio.run(main())