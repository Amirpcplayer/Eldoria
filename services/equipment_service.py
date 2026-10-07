from __future__ import annotations

from sqlalchemy import select

from database.database import AsyncSessionLocal

from models.character import Character
from models.equipment import Equipment, CharacterEquipment

from services.quest_service import record_equipment_equipped


# ============================================================
# CONSTANTS
# ============================================================

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


# ============================================================
# CHARACTER
# ============================================================

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


# ============================================================
# EQUIPMENT
# ============================================================

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
            .where(
                Equipment.is_active.is_(True)
            )
            .order_by(
                Equipment.required_level.asc(),
                Equipment.id.asc(),
            )
        )

        return list(result.scalars().all())


# ============================================================
# CHARACTER EQUIPMENT
# ============================================================

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
                Equipment.is_active.is_(True),
                CharacterEquipment.quantity > 0,
            )
            .order_by(
                Equipment.equipment_type.asc(),
                Equipment.required_level.asc(),
                Equipment.id.asc(),
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
                Equipment.equipment_type.asc(),
                Equipment.id.asc(),
            )
        )

        return list(result.all())


async def get_inventory(
    telegram_id: int,
) -> list[tuple[CharacterEquipment, Equipment]]:

    return await get_character_equipments(
        telegram_id
    )


# ============================================================
# ADD EQUIPMENT
# ============================================================

async def add_equipment(
    telegram_id: int,
    equipment_id: int,
    quantity: int = 1,
) -> tuple[bool, str]:

    if quantity <= 0:
        return False, "❌ مقدار باید بیشتر از صفر باشد."

    async with AsyncSessionLocal() as session:

        character_result = await session.execute(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        character = character_result.scalar_one_or_none()

        if character is None:
            return False, "❌ قهرمان پیدا نشد."

        equipment_result = await session.execute(
            select(Equipment).where(
                Equipment.id == equipment_id,
                Equipment.is_active.is_(True),
            )
        )

        equipment = equipment_result.scalar_one_or_none()

        if equipment is None:
            return False, "❌ تجهیزات پیدا نشد."

        result = await session.execute(
            select(CharacterEquipment).where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipment_id == equipment.id,
            )
        )

        character_equipment = result.scalar_one_or_none()

        if character_equipment is None:

            character_equipment = CharacterEquipment(
                character_id=character.id,
                equipment_id=equipment.id,
                quantity=quantity,
                equipped=False,
            )

            session.add(character_equipment)

        else:

            character_equipment.quantity += quantity

        await session.commit()

        return (
            True,
            f"✅ {equipment.name} ×{quantity} به موجودی اضافه شد.",
        )


# ============================================================
# EQUIP EQUIPMENT
# ============================================================

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
            return False, "❌ قهرمان پیدا نشد."

        equipment_result = await session.execute(
            select(Equipment).where(
                Equipment.id == equipment_id,
                Equipment.is_active.is_(True),
            )
        )

        equipment = equipment_result.scalar_one_or_none()

        if equipment is None:
            return False, "❌ تجهیزات پیدا نشد."

        if character.level < equipment.required_level:
            return (
                False,
                f"❌ برای استفاده از {equipment.name} "
                f"به سطح {equipment.required_level} نیاز داری.",
            )

        inventory_result = await session.execute(
            select(CharacterEquipment).where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipment_id == equipment.id,
            )
        )

        character_equipment = (
            inventory_result.scalar_one_or_none()
        )

        if character_equipment is None:
            return False, "❌ این تجهیزات در موجودی تو نیست."

        if character_equipment.quantity <= 0:
            return False, "❌ تعداد این تجهیزات صفر است."

        if character_equipment.equipped:
            return False, "⚠️ این تجهیزات از قبل مجهز است."

        # فقط یک وسیله از هر نوع می‌تواند مجهز باشد.
        equipped_result = await session.execute(
            select(CharacterEquipment)
            .join(
                Equipment,
                Equipment.id == CharacterEquipment.equipment_id,
            )
            .where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipped.is_(True),
                Equipment.equipment_type == equipment.equipment_type,
            )
        )

        old_items = equipped_result.scalars().all()

        for old_item in old_items:
            old_item.equipped = False

        character_equipment.equipped = True

        await session.commit()

        try:
            await record_equipment_equipped(
                telegram_id,
                equipment.id,
            )
        except Exception:
            pass

        return (
            True,
            f"✅ {equipment.name} با موفقیت مجهز شد.",
        )


# ============================================================
# UNEQUIP EQUIPMENT
# ============================================================

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
            return False, "❌ قهرمان پیدا نشد."

        result = await session.execute(
            select(
                CharacterEquipment,
                Equipment,
            )
            .join(
                Equipment,
                Equipment.id == CharacterEquipment.equipment_id,
            )
            .where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipment_id == equipment_id,
            )
        )

        row = result.first()

        if row is None:
            return False, "❌ این تجهیزات در موجودی تو نیست."

        character_equipment, equipment = row

        if not character_equipment.equipped:
            return False, "⚠️ این تجهیزات مجهز نیست."

        character_equipment.equipped = False

        await session.commit()

        return (
            True,
            f"✅ {equipment.name} از حالت تجهیز خارج شد.",
        )


# ============================================================
# EQUIPMENT STATS
# ============================================================

def _create_empty_stats() -> dict[str, int]:

    return {
        "attack": 0,
        "magic_power": 0,
        "defense": 0,
        "magic_defense": 0,
        "hp": 0,
        "mana": 0,
        "speed": 0,
        "accuracy": 0,
        "critical": 0,
    }


async def get_equipment_stats(
    telegram_id: int,
) -> dict[str, int]:

    stats = _create_empty_stats()

    equipped = await get_equipped_equipments(
        telegram_id
    )

    for _, equipment in equipped:

        for stat in STAT_FIELDS:

            value = getattr(
                equipment,
                stat,
                0,
            )

            if value is None:
                value = 0

            stats[stat] += int(value)

    return stats


async def calculate_equipment_stats(
    telegram_id: int,
) -> dict[str, int]:

    return await get_equipment_stats(
        telegram_id
    )


# ============================================================
# FINAL CHARACTER STATS
# ============================================================

async def get_final_character_stats(
    telegram_id: int,
    base_stats: dict[str, int] | None = None,
) -> dict[str, int]:

    character = await get_character(
        telegram_id
    )

    if character is None:
        return _create_empty_stats()

    equipment_stats = await get_equipment_stats(
        telegram_id
    )

    # --------------------------------------------------------
    # Base stats
    # --------------------------------------------------------

    if base_stats is None:

        base_stats = {
            "attack": int(character.attack),
            "magic_power": int(character.magic_power),
            "defense": int(character.defense),
            "magic_defense": int(character.magic_defense),

            # مهم:
            # HP و Mana برای شروع Battle از MAX استفاده می‌شوند.
            "hp": int(character.max_hp),
            "mana": int(character.max_mana),

            "speed": int(character.speed),
            "accuracy": int(character.accuracy),
            "critical": int(character.critical),
        }

    final_stats = {}

    for stat in STAT_FIELDS:

        final_stats[stat] = (
            int(base_stats.get(stat, 0))
            + int(equipment_stats.get(stat, 0))
        )

    return final_stats


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

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