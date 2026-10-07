from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.inventory import Inventory
from models.item import Item


async def add_item(
    character_id: int,
    item_id: int,
    quantity: int = 1,
) -> bool:

    if quantity <= 0:
        return False

    async with AsyncSessionLocal() as session:

        item = await session.scalar(
            select(Item).where(Item.id == item_id)
        )

        if item is None:
            return False

        inventory_item = await session.scalar(
            select(Inventory).where(
                Inventory.character_id == character_id,
                Inventory.item_id == item_id,
            )
        )

        if inventory_item:
            inventory_item.quantity += quantity

        else:
            inventory_item = Inventory(
                character_id=character_id,
                item_id=item_id,
                quantity=quantity,
            )

            session.add(inventory_item)

        await session.commit()

        return True


async def remove_item(
    character_id: int,
    item_id: int,
    quantity: int = 1,
) -> bool:

    if quantity <= 0:
        return False

    async with AsyncSessionLocal() as session:

        inventory_item = await session.scalar(
            select(Inventory).where(
                Inventory.character_id == character_id,
                Inventory.item_id == item_id,
            )
        )

        if inventory_item is None:
            return False

        if inventory_item.quantity < quantity:
            return False

        inventory_item.quantity -= quantity

        if inventory_item.quantity == 0:
            await session.delete(inventory_item)

        await session.commit()

        return True


async def get_inventory(
    character_id: int,
) -> list[tuple[Inventory, Item]]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Inventory, Item)
            .join(
                Item,
                Inventory.item_id == Item.id,
            )
            .where(
                Inventory.character_id == character_id
            )
            .order_by(Inventory.id)
        )

        return list(result.all())


async def sell_item(
    telegram_id: int,
    item_id: int,
    quantity: int = 1,
) -> tuple[bool, str]:

    # فروش در صندوقچه همیشه فقط یک عدد است
    if quantity != 1:
        return False, "❌ در هر بار فقط یک عدد آیتم فروخته می‌شود."

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return False, "❌ قهرمان پیدا نشد."

        inventory_item = await session.scalar(
            select(Inventory).where(
                Inventory.character_id == character.id,
                Inventory.item_id == item_id,
            )
        )

        if inventory_item is None:
            return False, "❌ این آیتم در صندوقچه تو وجود ندارد."

        item = await session.scalar(
            select(Item).where(
                Item.id == item_id
            )
        )

        if item is None:
            return False, "❌ آیتم پیدا نشد."

        if not item.is_tradeable:
            return False, "❌ این آیتم قابل فروش نیست."

        if item.sell_price <= 0:
            return False, "❌ این آیتم قیمت فروش ندارد."

        gold_received = item.sell_price

        # فقط یک عدد از آیتم کم می‌شود
        inventory_item.quantity -= 1

        if inventory_item.quantity == 0:
            await session.delete(inventory_item)

        # اضافه شدن Gold
        character.gold += gold_received

        current_gold = character.gold

        await session.commit()

        return (
            True,
            f"✅ فروش {item.name} با موفقیت انجام شد.\n\n"
            f"💰 +{gold_received} Gold به حساب شما اضافه شد.\n"
            f"💰 Gold فعلی: {current_gold}"
        )