from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.inventory import Inventory
from models.item import Item


async def add_item(character_id: int, item_id: int, quantity: int = 1) -> bool:
    if quantity <= 0:
        return False

    async with AsyncSessionLocal() as session:
        item = await session.scalar(select(Item).where(Item.id == item_id))
        if item is None:
            return False

        inventory_item = await session.scalar(
            select(Inventory).where(
                Inventory.character_id == character_id,
                Inventory.item_id == item_id,
            )
        )
        if inventory_item is None:
            session.add(Inventory(
                character_id=character_id,
                item_id=item_id,
                quantity=quantity,
            ))
        else:
            inventory_item.quantity += quantity

        await session.commit()
        return True


async def remove_item(character_id: int, item_id: int, quantity: int = 1) -> bool:
    if quantity <= 0:
        return False

    async with AsyncSessionLocal() as session:
        inventory_item = await session.scalar(
            select(Inventory).where(
                Inventory.character_id == character_id,
                Inventory.item_id == item_id,
            ).with_for_update()
        )
        if inventory_item is None or inventory_item.quantity < quantity:
            return False

        inventory_item.quantity -= quantity
        if inventory_item.quantity == 0:
            await session.delete(inventory_item)

        await session.commit()
        return True


async def get_inventory(character_id: int) -> list[tuple[Inventory, Item]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Inventory, Item)
            .join(Item, Inventory.item_id == Item.id)
            .where(
                Inventory.character_id == character_id,
                Inventory.quantity > 0,
            )
            .order_by(Inventory.id)
        )
        return list(result.all())


async def sell_item(telegram_id: int, item_id: int, quantity: int = 1) -> tuple[bool, str]:
    if quantity != 1:
        return False, "در این بخش، هر بار فقط یک عدد آیتم فروخته می‌شود."

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == telegram_id)
            .with_for_update()
        )
        if character is None:
            return False, "شخصیت شما پیدا نشد."

        item = await session.scalar(
            select(Item).where(Item.id == item_id)
        )
        if item is None:
            return False, "این آیتم پیدا نشد."

        inventory_item = await session.scalar(
            select(Inventory)
            .where(
                Inventory.character_id == character.id,
                Inventory.item_id == item_id,
            )
            .with_for_update()
        )
        if inventory_item is None or inventory_item.quantity < 1:
            return False, "این آیتم در صندوقچه شما وجود ندارد."

        if item.sell_price <= 0:
            return False, "این آیتم قابل فروش به فروشگاه نیست."

        gold_received = item.sell_price
        inventory_item.quantity -= 1
        if inventory_item.quantity == 0:
            await session.delete(inventory_item)

        character.gold += gold_received
        current_gold = character.gold
        item_name = item.name
        await session.commit()

    return (
        True,
        f"✅ آیتم «{item_name}» با موفقیت فروخته شد.\n\n"
        f"💰 دریافتی: +{gold_received} Gold\n"
        f"💰 موجودی فعلی: {current_gold} Gold",
    )
