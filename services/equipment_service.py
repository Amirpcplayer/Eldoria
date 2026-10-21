from __future__ import annotations

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.equipment import Equipment, CharacterEquipment
from services.quest_service import record_equipment_equipped


EQUIPMENT_TYPES = {
    "weapon",
    "helmet",
    "armor",
    "boots",
    "ring",
    "necklace",
}


STAT_FIELDS = (
    "attack",
    "magic_power",
    "defense",
    "magic_defense",
    "hp",
    "mana",
    "speed",
    "accuracy",
    "critical",
)


async def get_character(
    telegram_id: int,
) -> Character | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )
        return result.scalar_one_or_none()


async def get_equipment(
    equipment_id: int,
) -> Equipment | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Equipment).where(
                Equipment.id == equipment_id
            )
        )
        return result.scalar_one_or_none()


async def get_all_equipments() -> list[Equipment]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Equipment)
            .where(Equipment.is_active.is_(True))
            .order_by(
                Equipment.required_level,
                Equipment.id,
            )
        )
        return list(result.scalars().all())


async def get_character_equipment(
    telegram_id: int,
    equipment_id: int,
) -> CharacterEquipment | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CharacterEquipment)
            .join(
                Character,
                Character.id == CharacterEquipment.character_id,
            )
            .where(
                Character.telegram_id == telegram_id,
                CharacterEquipment.equipment_id == equipment_id,
            )
        )
        return result.scalar_one_or_none()


async def get_character_equipments(
    telegram_id: int,
) -> list[tuple[CharacterEquipment, Equipment]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                CharacterEquipment,
                Equipment,
            )
            .join(
                Character,
                Character.id == CharacterEquipment.character_id,
            )
            .join(
                Equipment,
                Equipment.id == CharacterEquipment.equipment_id,
            )
            .where(
                Character.telegram_id == telegram_id,
                CharacterEquipment.quantity > 0,
                Equipment.is_active.is_(True),
            )
            .order_by(
                Equipment.equipment_type,
                Equipment.required_level,
                Equipment.id,
            )
        )

        return list(result.all())


async def get_equipped_equipments(
    telegram_id: int,
) -> list[tuple[CharacterEquipment, Equipment]]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                CharacterEquipment,
                Equipment,
            )
            .join(
                Character,
                Character.id == CharacterEquipment.character_id,
            )
            .join(
                Equipment,
                Equipment.id == CharacterEquipment.equipment_id,
            )
            .where(
                Character.telegram_id == telegram_id,
                CharacterEquipment.equipped.is_(True),
                CharacterEquipment.quantity > 0,
                Equipment.is_active.is_(True),
            )
            .order_by(
                Equipment.equipment_type,
                Equipment.id,
            )
        )

        return list(result.all())


async def get_inventory(
    telegram_id: int,
) -> list[tuple[CharacterEquipment, Equipment]]:
    return await get_character_equipments(telegram_id)


async def add_equipment(
    telegram_id: int,
    equipment_id: int,
    quantity: int = 1,
) -> tuple[bool, str]:

    if quantity <= 0:
        return False, "تعداد تجهیزات باید بیشتر از صفر باشد."

    async with AsyncSessionLocal() as session:
        character_result = await session.execute(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )
        character = character_result.scalar_one_or_none()

        if character is None:
            return False, "شخصیت شما پیدا نشد."

        equipment_result = await session.execute(
            select(Equipment).where(
                Equipment.id == equipment_id,
                Equipment.is_active.is_(True),
            )
        )
        equipment = equipment_result.scalar_one_or_none()

        if equipment is None:
            return False, "این وسیله وجود ندارد یا غیرفعال است."

        if equipment.equipment_type not in EQUIPMENT_TYPES:
            return False, "نوع این وسیله معتبر نیست."

        inventory_result = await session.execute(
            select(CharacterEquipment).where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipment_id == equipment.id,
            )
        )

        inventory_item = inventory_result.scalar_one_or_none()

        if inventory_item is None:
            inventory_item = CharacterEquipment(
                character_id=character.id,
                equipment_id=equipment.id,
                quantity=quantity,
                equipped=False,
            )
            session.add(inventory_item)
        else:
            inventory_item.quantity += quantity

        await session.commit()

        return (
            True,
            f"تعداد {quantity} عدد «{equipment.name}» "
            "به صندوقچه اضافه شد.",
        )


async def add_equipment_to_character(
    telegram_id: int,
    equipment_id: int,
    quantity: int = 1,
) -> tuple[bool, str]:
    return await add_equipment(
        telegram_id,
        equipment_id,
        quantity,
    )


async def equip_equipment(
    telegram_id: int,
    equipment_id: int,
) -> tuple[bool, str]:

    async with AsyncSessionLocal() as session:
        character_result = await session.execute(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )
        character = character_result.scalar_one_or_none()

        if character is None:
            return False, "شخصیت شما پیدا نشد."

        equipment_result = await session.execute(
            select(Equipment).where(
                Equipment.id == equipment_id,
                Equipment.is_active.is_(True),
            )
        )
        equipment = equipment_result.scalar_one_or_none()

        if equipment is None:
            return False, "این وسیله وجود ندارد یا غیرفعال است."

        if equipment.equipment_type not in EQUIPMENT_TYPES:
            return False, "نوع این وسیله معتبر نیست."

        character_level = int(character.level or 1)
        required_level = int(
            equipment.required_level or 1
        )

        if character_level < required_level:
            return (
                False,
                f"برای تجهیز «{equipment.name}» "
                f"باید حداقل سطح {required_level} را داشته باشید.",
            )

        inventory_result = await session.execute(
            select(CharacterEquipment).where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipment_id == equipment.id,
                CharacterEquipment.quantity > 0,
            )
        )

        inventory_item = inventory_result.scalar_one_or_none()

        if inventory_item is None:
            return False, "این وسیله در صندوقچه شما نیست."

        if inventory_item.equipped:
            return False, "این وسیله از قبل مجهز شده است."

        equipped_result = await session.execute(
            select(CharacterEquipment)
            .join(
                Equipment,
                Equipment.id == CharacterEquipment.equipment_id,
            )
            .where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipped.is_(True),
                CharacterEquipment.quantity > 0,
                Equipment.equipment_type == equipment.equipment_type,
            )
        )

        old_items = list(
            equipped_result.scalars().all()
        )

        for old_item in old_items:
            old_item.equipped = False

        inventory_item.equipped = True

        await session.commit()

    try:
        await record_equipment_equipped(
            telegram_id,
            equipment_id,
        )
    except Exception:
        pass

    return (
        True,
        f"«{equipment.name}» با موفقیت مجهز شد.",
    )


async def unequip_equipment(
    telegram_id: int,
    equipment_id: int,
) -> tuple[bool, str]:

    async with AsyncSessionLocal() as session:
        character_result = await session.execute(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )
        character = character_result.scalar_one_or_none()

        if character is None:
            return False, "شخصیت شما پیدا نشد."

        inventory_result = await session.execute(
            select(CharacterEquipment).where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipment_id == equipment_id,
                CharacterEquipment.equipped.is_(True),
                CharacterEquipment.quantity > 0,
            )
        )

        inventory_item = inventory_result.scalar_one_or_none()

        if inventory_item is None:
            return False, "این وسیله در حال حاضر مجهز نیست."

        equipment_result = await session.execute(
            select(Equipment).where(
                Equipment.id == equipment_id
            )
        )

        equipment = equipment_result.scalar_one_or_none()

        inventory_item.equipped = False

        await session.commit()

        equipment_name = (
            equipment.name
            if equipment
            else "تجهیزات"
        )

    return (
        True,
        f"«{equipment_name}» از حالت تجهیز خارج شد.",
    )


def _create_empty_stats() -> dict[str, int]:
    return {
        stat: 0
        for stat in STAT_FIELDS
    }


async def get_equipment_stats(
    telegram_id: int,
) -> dict[str, int]:

    stats = _create_empty_stats()

    equipped = await get_equipped_equipments(
        telegram_id
    )

    for character_equipment, equipment in equipped:
        enhancement_level = int(getattr(character_equipment, "enhancement_level", 0) or 0)
        for stat in STAT_FIELDS:
            value = int(getattr(equipment, stat, 0) or 0)
            if value:
                value += int(value * 0.05 * enhancement_level)
            stats[stat] += value

    return stats


async def calculate_equipment_stats(
    telegram_id: int,
) -> dict[str, int]:
    return await get_equipment_stats(
        telegram_id
    )


async def get_final_character_stats(
    telegram_id: int,
    base_stats: dict[str, int] | None = None,
) -> dict[str, int]:

    character = await get_character(
        telegram_id
    )

    if character is None:
        return _create_empty_stats()

    if base_stats is None:
        # مسیر مرکزی: مبارزه، دانجن و PvP باید از یک محاسبه استفاده کنند.
        from services.character_stats_service import calculate_character_combat_stats
        central = await calculate_character_combat_stats(character)
        return {
            "attack": int(central.attack),
            "magic_power": int(central.magic_power),
            "defense": int(central.defense),
            "magic_defense": int(central.magic_defense),
            "hp": int(central.max_hp),
            "mana": int(central.max_mana),
            "speed": int(central.speed),
            "accuracy": int(central.accuracy),
            "critical": int(central.critical),
            "luck": int(central.luck),
        }

    equipment_stats = await get_equipment_stats(
        telegram_id
    )

    if base_stats is None:
        base_stats = {
            "attack": int(character.attack or 0),
            "magic_power": int(
                character.magic_power or 0
            ),
            "defense": int(
                character.defense or 0
            ),
            "magic_defense": int(
                character.magic_defense or 0
            ),
            "hp": int(character.max_hp or 0),
            "mana": int(character.max_mana or 0),
            "speed": int(character.speed or 0),
            "accuracy": int(
                character.accuracy or 0
            ),
            "critical": int(
                character.critical or 0
            ),
        }

    return {
        stat: int(
            base_stats.get(stat, 0) or 0
        )
        + int(
            equipment_stats.get(stat, 0) or 0
        )
        for stat in STAT_FIELDS
    }


async def equip_item(
    telegram_id: int,
    equipment_id: int,
) -> tuple[bool, str]:
    return await equip_equipment(
        telegram_id,
        equipment_id,
    )


async def unequip_item(
    telegram_id: int,
    equipment_id: int,
) -> tuple[bool, str]:
    return await unequip_equipment(
        telegram_id,
        equipment_id,
    )


async def add_item(
    telegram_id: int,
    equipment_id: int,
    quantity: int = 1,
) -> tuple[bool, str]:
    return await add_equipment(
        telegram_id,
        equipment_id,
        quantity,
    )


async def get_equipped_items(
    telegram_id: int,
) -> list[tuple[CharacterEquipment, Equipment]]:
    return await get_equipped_equipments(
        telegram_id
    )


async def get_character_equipment_list(
    telegram_id: int,
) -> list[tuple[CharacterEquipment, Equipment]]:
    return await get_character_equipments(
        telegram_id
    )