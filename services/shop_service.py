from __future__ import annotations

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.equipment import CharacterEquipment, Equipment
from models.inventory import Inventory
from models.item import Item
from services.potion_rules import POTION_SHOP_ITEMS


SHOP_ITEM_TYPES = ("potion", "material", "scroll")
SHOP_EQUIPMENT_TYPE = "equipment"


def _format_gold(value: int) -> str:
    return f"{int(value):,}"


async def get_shop_items(
    item_type: str | None = None,
) -> list[Item]:
    async with AsyncSessionLocal() as session:
        query = (
            select(Item)
            .where(
                Item.buy_price > 0,
                Item.item_type.in_(SHOP_ITEM_TYPES),
                (Item.item_type != "potion") | Item.name.in_(tuple(POTION_SHOP_ITEMS)),
            )
            .order_by(Item.item_type, Item.rarity, Item.buy_price, Item.id)
        )

        if item_type is not None:
            query = query.where(Item.item_type == item_type)
        if item_type == "potion":
            query = query.where(Item.name.in_(tuple(POTION_SHOP_ITEMS)))

        result = await session.execute(query)
        return list(result.scalars().all())


async def get_shop_equipment() -> list[Equipment]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Equipment)
            .where(
                Equipment.is_active.is_(True),
                Equipment.shop_price > 0,
            )
            .order_by(
                Equipment.required_level,
                Equipment.shop_price,
                Equipment.id,
            )
        )
        return list(result.scalars().all())


async def get_shop_item(item_id: int) -> Item | None:
    async with AsyncSessionLocal() as session:
        query = select(Item).where(
            Item.id == item_id,
            Item.buy_price > 0,
            Item.item_type.in_(SHOP_ITEM_TYPES),
        )
        query = query.where(
            (Item.item_type != "potion") | Item.name.in_(tuple(POTION_SHOP_ITEMS))
        )
        return await session.scalar(query)


async def get_shop_equipment_item(equipment_id: int) -> Equipment | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Equipment).where(
                Equipment.id == equipment_id,
                Equipment.is_active.is_(True),
                Equipment.shop_price > 0,
            )
        )


async def buy_item(
    telegram_id: int,
    item_id: int,
    quantity: int = 1,
) -> tuple[bool, str]:
    if quantity <= 0:
        return False, "⚠️ تعداد خرید باید بیشتر از صفر باشد."

    if quantity > 99:
        return False, "⚠️ در هر خرید حداکثر ۹۹ عدد می‌توانی بخری."

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == telegram_id)
            .with_for_update()
        )

        if character is None:
            return False, "❌ قهرمان پیدا نشد."

        item_query = select(Item).where(
            Item.id == item_id,
            Item.buy_price > 0,
            Item.item_type.in_(SHOP_ITEM_TYPES),
        )
        item_query = item_query.where(
            (Item.item_type != "potion") | Item.name.in_(tuple(POTION_SHOP_ITEMS))
        )
        item = await session.scalar(item_query)

        if item is None:
            return False, "❌ این آیتم در فروشگاه موجود نیست."

        if "سطح ۸۰" in item.name and int(character.level or 1) < 80:
            return False, "🔒 این معجون از سطح ۸۰ به بالا قابل خرید است."

        total_price = int(item.buy_price) * quantity

        if character.gold < total_price:
            return (
                False,
                "💰 Gold کافی نداری.\n\n"
                f"قیمت: {_format_gold(total_price)} Gold\n"
                f"موجودی: {_format_gold(character.gold)} Gold",
            )

        inventory_item = await session.scalar(
            select(Inventory)
            .where(
                Inventory.character_id == character.id,
                Inventory.item_id == item.id,
            )
            .with_for_update()
        )

        if inventory_item is None:
            inventory_item = Inventory(
                character_id=character.id,
                item_id=item.id,
                quantity=quantity,
            )
            session.add(inventory_item)
        else:
            inventory_item.quantity += quantity

        character.gold -= total_price
        current_gold = character.gold

        await session.commit()

        return (
            True,
            "✅ خرید با موفقیت انجام شد!\n\n"
            f"🗃 {item.name}\n"
            f"📊 تعداد: ×{quantity}\n"
            f"💰 هزینه: {_format_gold(total_price)} Gold\n"
            f"💰 موجودی فعلی: {_format_gold(current_gold)} Gold",
        )


async def buy_equipment(
    telegram_id: int,
    equipment_id: int,
) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == telegram_id)
            .with_for_update()
        )

        if character is None:
            return False, "❌ قهرمان پیدا نشد."

        equipment = await session.scalar(
            select(Equipment).where(
                Equipment.id == equipment_id,
                Equipment.is_active.is_(True),
                Equipment.shop_price > 0,
            )
        )

        if equipment is None:
            return False, "❌ این تجهیز در فروشگاه موجود نیست."

        if character.level < equipment.required_level:
            return (
                False,
                f"🔒 برای خرید «{equipment.name}» باید حداقل Level "
                f"{equipment.required_level} باشی.",
            )

        existing = await session.scalar(
            select(CharacterEquipment)
            .where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipment_id == equipment.id,
                CharacterEquipment.quantity > 0,
            )
            .with_for_update()
        )

        if existing is not None:
            return (
                False,
                f"⚠️ «{equipment.name}» را قبلاً داری.\n\n"
                "تجهیزات فروشگاه قابل خریدِ تکراری نیستند.",
            )

        price = int(equipment.shop_price)

        if character.gold < price:
            return (
                False,
                "💰 Gold کافی نداری.\n\n"
                f"قیمت: {_format_gold(price)} Gold\n"
                f"موجودی: {_format_gold(character.gold)} Gold",
            )

        session.add(
            CharacterEquipment(
                character_id=character.id,
                equipment_id=equipment.id,
                quantity=1,
                equipped=False,
            )
        )

        character.gold -= price
        current_gold = character.gold

        await session.commit()

        return (
            True,
            "✅ خرید تجهیزات با موفقیت انجام شد!\n\n"
            f"⚔️ {equipment.name}\n"
            f"💰 هزینه: {_format_gold(price)} Gold\n"
            f"💰 موجودی فعلی: {_format_gold(current_gold)} Gold",
        )
