import pytest
from sqlalchemy import delete, select

from database.database import AsyncSessionLocal
from models.character import Character
from models.equipment import CharacterEquipment, Equipment
from models.inventory import Inventory
from models.item import Item
from services.shop_service import buy_equipment, buy_item


TEST_TELEGRAM_ID = 999999991


@pytest.fixture(autouse=True)
async def shop_test_character():
    async with AsyncSessionLocal() as session:
        old = await session.scalar(
            select(Character).where(
                Character.telegram_id == TEST_TELEGRAM_ID
            )
        )
        if old is not None:
            await session.delete(old)
            await session.commit()

        character = Character(
            telegram_id=TEST_TELEGRAM_ID,
            name="ShopTestHero",
            race="human",
            level=10,
            gold=5000,
        )
        session.add(character)
        await session.commit()

    yield

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == TEST_TELEGRAM_ID
            )
        )
        if character is not None:
            await session.delete(character)
            await session.commit()


@pytest.mark.asyncio
async def test_buy_stackable_item():
    async with AsyncSessionLocal() as session:
        item = Item(
            name="🪨 مادهٔ تست شاپ",
            description="test",
            item_type="material",
            rarity="common",
            sell_price=10,
            buy_price=100,
            is_tradeable=True,
        )
        session.add(item)
        await session.commit()
        item_id = item.id

    success, _ = await buy_item(
        TEST_TELEGRAM_ID,
        item_id,
        2,
    )

    assert success is True

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == TEST_TELEGRAM_ID
            )
        )
        inventory = await session.scalar(
            select(Inventory).where(
                Inventory.character_id == character.id,
                Inventory.item_id == item_id,
            )
        )

        assert character.gold == 4800
        assert inventory is not None
        assert inventory.quantity == 2

        await session.delete(inventory)
        await session.delete(item)
        await session.commit()


@pytest.mark.asyncio
async def test_buy_rejects_insufficient_gold():
    async with AsyncSessionLocal() as session:
        item = Item(
            name="💎 تست گران",
            description="test",
            item_type="material",
            rarity="rare",
            sell_price=100,
            buy_price=99999,
            is_tradeable=True,
        )
        session.add(item)
        await session.commit()
        item_id = item.id

    success, _ = await buy_item(
        TEST_TELEGRAM_ID,
        item_id,
    )

    assert success is False

    async with AsyncSessionLocal() as session:
        item = await session.get(Item, item_id)
        assert item is not None
        await session.delete(item)
        await session.commit()


@pytest.mark.asyncio
async def test_buy_equipment_once():
    async with AsyncSessionLocal() as session:
        equipment = Equipment(
            name="⚔️ تجهیز تست شاپ",
            description="test",
            equipment_type="weapon",
            rarity="common",
            required_level=1,
            shop_price=500,
            attack=10,
        )
        session.add(equipment)
        await session.commit()
        equipment_id = equipment.id

    success, _ = await buy_equipment(
        TEST_TELEGRAM_ID,
        equipment_id,
    )
    assert success is True

    success, _ = await buy_equipment(
        TEST_TELEGRAM_ID,
        equipment_id,
    )
    assert success is False

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == TEST_TELEGRAM_ID
            )
        )
        owned = await session.scalar(
            select(CharacterEquipment).where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipment_id == equipment_id,
            )
        )

        assert character.gold == 4500
        assert owned is not None
        assert owned.quantity == 1

        await session.delete(owned)
        equipment = await session.get(Equipment, equipment_id)
        if equipment is not None:
            await session.delete(equipment)
        await session.commit()


@pytest.mark.asyncio
async def test_buy_equipment_rejects_required_level():
    async with AsyncSessionLocal() as session:
        equipment = Equipment(
            name="🔒 تجهیز سطح بالا",
            description="test",
            equipment_type="weapon",
            rarity="rare",
            required_level=99,
            shop_price=500,
            attack=100,
        )
        session.add(equipment)
        await session.commit()
        equipment_id = equipment.id

    success, _ = await buy_equipment(
        TEST_TELEGRAM_ID,
        equipment_id,
    )

    assert success is False

    async with AsyncSessionLocal() as session:
        equipment = await session.get(Equipment, equipment_id)
        if equipment is not None:
            await session.delete(equipment)
        await session.commit()


def test_shop_potion_catalog_is_restricted_to_four_named_items():
    from services.potion_rules import POTION_SHOP_ITEMS
    assert len(POTION_SHOP_ITEMS) == 4
    assert {entry["ratio"] for entry in POTION_SHOP_ITEMS.values()} == {0.20, 0.40}
    assert {entry["kind"] for entry in POTION_SHOP_ITEMS.values()} == {"hp", "mana"}
