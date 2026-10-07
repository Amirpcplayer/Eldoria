from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.inventory import Inventory
from models.item import Item


async def get_item(
    item_id: int,
) -> Item | None:

    async with AsyncSessionLocal() as session:

        return await session.scalar(
            select(Item).where(
                Item.id == item_id
            )
        )


async def get_item_heal_amount(
    item: Item,
) -> int:

    potion_heal = {
        "🧪 معجون سلامتی": 40,
        "🧪 معجون سلامتی بزرگ": 80,
    }

    return potion_heal.get(
        item.name,
        0,
    )


async def get_healing_potions(
    character_id: int,
) -> list[tuple[Inventory, Item, int]]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Inventory, Item)
            .join(
                Item,
                Inventory.item_id == Item.id,
            )
            .where(
                Inventory.character_id == character_id,
                Item.item_type == "potion",
                Inventory.quantity > 0,
            )
            .order_by(Inventory.id)
        )

        potions = []

        for inventory_item, item in result.all():

            heal_amount = await get_item_heal_amount(
                item
            )

            if heal_amount <= 0:
                continue

            potions.append(
                (
                    inventory_item,
                    item,
                    heal_amount,
                )
            )

        return potions


async def sell_item(
    telegram_id: int,
    item_id: int,
    quantity: int = 1,
) -> tuple[bool, str]:

    if quantity != 1:
        return (
            False,
            "⚠️ فقط یک عدد آیتم در هر فروش قابل فروش است.",
        )

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return (
                False,
                "❌ قهرمان پیدا نشد.",
            )

        item = await session.scalar(
            select(Item).where(
                Item.id == item_id
            )
        )

        if item is None:
            return (
                False,
                "❌ آیتم پیدا نشد.",
            )

        if item.sell_price <= 0:
            return (
                False,
                "⚠️ این آیتم قابل فروش نیست.",
            )

        inventory_item = await session.scalar(
            select(Inventory)
            .where(
                Inventory.character_id == character.id,
                Inventory.item_id == item_id,
            )
            .with_for_update()
        )

        if inventory_item is None:
            return (
                False,
                "❌ این آیتم در صندوقچه شما وجود ندارد.",
            )

        if inventory_item.quantity < quantity:
            return (
                False,
                "❌ تعداد کافی از این آیتم را نداری.",
            )

        gold_received = item.sell_price * quantity

        inventory_item.quantity -= quantity

        if inventory_item.quantity <= 0:
            await session.delete(
                inventory_item
            )

        character.gold += gold_received

        current_gold = character.gold

        await session.commit()

        return (
            True,
            f"✅ فروش {item.name} با موفقیت انجام شد.\n\n"
            f"📦 تعداد: {quantity}\n"
            f"💰 +{gold_received} Gold\n"
            f"💰 Gold فعلی: {current_gold}",
        )