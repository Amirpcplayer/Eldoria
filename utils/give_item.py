import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.item import Item
from services.inventory_service import add_item


TELEGRAM_ID = 8537258392
ITEM_NAME = "🧪 معجون سلامتی"
QUANTITY = 3


async def give_item():

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == TELEGRAM_ID
            )
        )

        if character is None:
            print("❌ Character not found.")
            return

        item = await session.scalar(
            select(Item).where(
                Item.name == ITEM_NAME
            )
        )

        if item is None:
            print("❌ Item not found.")
            return

        character_id = character.id
        item_id = item.id

    success = await add_item(
        character_id=character_id,
        item_id=item_id,
        quantity=QUANTITY,
    )

    if success:
        print(
            f"✅ {QUANTITY}x {ITEM_NAME} "
            f"added to {character.name}'s inventory."
        )
    else:
        print("❌ Failed to add item.")


if __name__ == "__main__":
    asyncio.run(give_item())