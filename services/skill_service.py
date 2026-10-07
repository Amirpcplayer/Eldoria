from sqlalchemy import select

from database.database import AsyncSessionLocal

from models.character import Character
from models.character_skill import CharacterSkill
from models.skill import Skill

from services.quest_service import record_skill_learned


# ============================================================
# Skill Configuration
# ============================================================

SKILL_MANA_GROWTH = {
    "fire": 8,
    "water": 8,
    "wind": 9,
    "earth": 10,
    "electro": 12,
    "ice": 13,
    "light": 18,
    "dark": 20,
}


SKILL_UPGRADE_COSTS = {
    1: {"xp": 500, "gold": 1000},
    2: {"xp": 1000, "gold": 2000},
    3: {"xp": 1500, "gold": 3500},
    4: {"xp": 2500, "gold": 5000},
    5: {"xp": 4000, "gold": 8000},
    6: {"xp": 6000, "gold": 12000},
    7: {"xp": 8500, "gold": 17000},
    8: {"xp": 12000, "gold": 24000},
    9: {"xp": 16000, "gold": 32000},
}


# ============================================================
# Skill Calculations
# ============================================================

def get_skill_power(
    skill: Skill,
    level: int,
) -> int:
    """
    محاسبه قدرت مهارت بر اساس Level.
    """

    level = max(1, level)

    return (
        skill.base_power
        + ((level - 1) * skill.power_per_level)
    )


def get_skill_mana_cost(
    skill: Skill,
    level: int,
) -> int:
    """
    محاسبه Mana Cost بر اساس Level.
    """

    level = max(1, level)

    growth = SKILL_MANA_GROWTH.get(
        skill.element,
        0,
    )

    return (
        skill.mana_cost
        + ((level - 1) * growth)
    )


def get_upgrade_cost(
    current_level: int,
) -> dict[str, int] | None:
    """
    هزینه ارتقای مهارت از Level فعلی به Level بعد.
    """

    return SKILL_UPGRADE_COSTS.get(
        current_level
    )


# ============================================================
# Character
# ============================================================

async def get_character(
    telegram_id: int,
) -> Character | None:

    async with AsyncSessionLocal() as session:

        return await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )


async def get_character_by_id(
    character_id: int,
) -> Character | None:

    async with AsyncSessionLocal() as session:

        return await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )


# ============================================================
# Skill Queries
# ============================================================

async def get_skill(
    skill_id: int,
) -> Skill | None:

    async with AsyncSessionLocal() as session:

        return await session.scalar(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )


async def get_all_skills() -> list[Skill]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Skill)
            .where(
                Skill.is_active.is_(True)
            )
            .order_by(
                Skill.unlock_level,
                Skill.id,
            )
        )

        return list(
            result.scalars().all()
        )


# ============================================================
# Character Skills
# ============================================================

async def get_character_skill(
    character_id: int,
    skill_id: int,
) -> CharacterSkill | None:

    async with AsyncSessionLocal() as session:

        return await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill_id,
            )
        )


async def get_character_skills(
    character_id: int,
) -> list[tuple[Skill, CharacterSkill]]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(
                Skill,
                CharacterSkill,
            )
            .join(
                CharacterSkill,
                CharacterSkill.skill_id == Skill.id,
            )
            .where(
                CharacterSkill.character_id == character_id,
                Skill.is_active.is_(True),
            )
            .order_by(
                CharacterSkill.slot,
                CharacterSkill.id,
            )
        )

        return list(
            result.all()
        )


async def get_unlocked_character_skills(
    character_id: int,
) -> list[tuple[Skill, CharacterSkill]]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(
                Skill,
                CharacterSkill,
            )
            .join(
                CharacterSkill,
                CharacterSkill.skill_id == Skill.id,
            )
            .where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.unlocked.is_(True),
                Skill.is_active.is_(True),
            )
            .order_by(
                CharacterSkill.slot,
                CharacterSkill.id,
            )
        )

        return list(
            result.all()
        )


# ============================================================
# Skill Slots
# ============================================================

def get_unlocked_skill_slots(
    character_level: int,
) -> int:
    """
    تعداد Slotهای باز شده بر اساس Level قهرمان.

    Level 1-19  -> 1 Slot
    Level 20-59 -> 2 Slots
    Level 60+   -> 3 Slots
    """

    if character_level >= 60:
        return 3

    if character_level >= 20:
        return 2

    return 1


def get_max_skill_slots(
    character_level: int,
) -> int:

    return get_unlocked_skill_slots(
        character_level
    )


async def get_used_skill_slots(
    character_id: int,
) -> int:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.unlocked.is_(True),
            )
        )

        return len(
            list(result.scalars().all())
        )


async def get_next_available_slot(
    character_id: int,
    character_level: int,
) -> int | None:

    max_slots = get_unlocked_skill_slots(
        character_level
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(CharacterSkill.slot).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.unlocked.is_(True),
            )
        )

        used_slots = {
            slot
            for slot in result.scalars().all()
            if slot is not None
        }

    for slot in range(
        1,
        max_slots + 1,
    ):
        if slot not in used_slots:
            return slot

    return None


# ============================================================
# Skill Unlock Rules
# ============================================================

def is_skill_unlocked_by_level(
    character_level: int,
    skill: Skill,
) -> bool:

    return (
        character_level >= skill.unlock_level
    )


async def can_learn_skill(
    character_id: int,
    skill_id: int,
) -> tuple[bool, str]:

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        if character is None:
            return (
                False,
                "❌ قهرمان پیدا نشد.",
            )

        skill = await session.scalar(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        if skill is None:
            return (
                False,
                "❌ مهارت پیدا نشد.",
            )

        existing = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill_id,
            )
        )

        if (
            existing is not None
            and existing.unlocked
        ):
            return (
                False,
                "❌ این مهارت را قبلاً یاد گرفته‌ای.",
            )

        if character.level < skill.unlock_level:
            return (
                False,
                (
                    "🔒 این مهارت هنوز باز نشده است.\n\n"
                    f"⭐ Level فعلی: {character.level}\n"
                    f"🔓 Level موردنیاز: {skill.unlock_level}"
                ),
            )

        max_slots = get_unlocked_skill_slots(
            character.level
        )

        used_slots_result = await session.execute(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.unlocked.is_(True),
            )
        )

        used_slots = len(
            list(
                used_slots_result.scalars().all()
            )
        )

        if used_slots >= max_slots:
            return (
                False,
                (
                    "🔒 تمام اسلات‌های مهارت پر شده‌اند.\n\n"
                    f"⚔️ اسلات‌ها: {used_slots}/{max_slots}"
                ),
            )

        return (
            True,
            "OK",
        )


# ============================================================
# Unlock Skill
# ============================================================

async def unlock_skill(
    telegram_id: int,
    skill_id: int,
) -> tuple[bool, str]:

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

        skill = await session.scalar(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        if skill is None:
            return (
                False,
                "❌ مهارت پیدا نشد.",
            )

        existing = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == skill_id,
            )
        )

        if (
            existing is not None
            and existing.unlocked
        ):
            return (
                False,
                "❌ این مهارت را قبلاً یاد گرفته‌ای.",
            )

        # ----------------------------------------------------
        # Level Check
        # ----------------------------------------------------

        if character.level < skill.unlock_level:
            return (
                False,
                (
                    "🔒 این مهارت هنوز باز نشده است.\n\n"
                    f"⭐ Level فعلی: {character.level}\n"
                    f"🔓 Level موردنیاز: {skill.unlock_level}"
                ),
            )

        # ----------------------------------------------------
        # Slot Check
        # ----------------------------------------------------

        max_slots = get_unlocked_skill_slots(
            character.level
        )

        result = await session.execute(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.unlocked.is_(True),
            )
        )

        used_skills = list(
            result.scalars().all()
        )

        if len(used_skills) >= max_slots:
            return (
                False,
                (
                    "🔒 تمام اسلات‌های مهارت پر شده‌اند.\n\n"
                    f"⚔️ اسلات‌ها: "
                    f"{len(used_skills)}/{max_slots}"
                ),
            )

        # ----------------------------------------------------
        # Find Free Slot
        # ----------------------------------------------------

        used_slot_numbers = {
            character_skill.slot
            for character_skill in used_skills
            if character_skill.slot is not None
        }

        free_slot = None

        for slot in range(
            1,
            max_slots + 1,
        ):
            if slot not in used_slot_numbers:
                free_slot = slot
                break

        if free_slot is None:
            return (
                False,
                "❌ اسلات خالی پیدا نشد.",
            )

        # ----------------------------------------------------
        # Create / Reactivate
        # ----------------------------------------------------

        if existing is None:

            character_skill = CharacterSkill(
                character_id=character.id,
                skill_id=skill.id,
                level=1,
                slot=free_slot,
                unlocked=True,
            )

            session.add(
                character_skill
            )

        else:

            existing.level = 1
            existing.slot = free_slot
            existing.unlocked = True

            character_skill = existing

        await session.commit()

    # --------------------------------------------------------
    # Quest Hook
    # --------------------------------------------------------

    try:
        await record_skill_learned(
            telegram_id,
            skill.id,
        )
    except Exception:
        pass

    return (
        True,
        (
            "🎉 <b>مهارت با موفقیت یاد گرفته شد!</b>\n\n"
            f"🔮 {skill.name}\n"
            "📈 Level: 1\n"
            f"⚔️ Slot: {free_slot}"
        ),
    )


# ============================================================
# Skill Upgrade Information
# ============================================================

async def get_skill_upgrade_info(
    telegram_id: int,
    skill_id: int,
) -> tuple[bool, str, dict | None]:

    async with AsyncSessionLocal() as session:

        # ----------------------------------------------------
        # Character
        # ----------------------------------------------------

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return (
                False,
                "❌ قهرمان پیدا نشد.",
                None,
            )

        # ----------------------------------------------------
        # Skill + Character Skill
        # ----------------------------------------------------

        result = await session.execute(
            select(
                Skill,
                CharacterSkill,
            )
            .join(
                CharacterSkill,
                CharacterSkill.skill_id == Skill.id,
            )
            .where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == skill_id,
                CharacterSkill.unlocked.is_(True),
                Skill.is_active.is_(True),
            )
        )

        row = result.first()

        if row is None:
            return (
                False,
                "❌ این مهارت را یاد نگرفته‌ای.",
                None,
            )

        skill, character_skill = row

        current_level = character_skill.level

        # ----------------------------------------------------
        # Max Level
        # ----------------------------------------------------

        if current_level >= skill.max_level:

            return (
                False,
                (
                    f"🔮 مهارت «{skill.name}» "
                    f"به حداکثر Level {skill.max_level} رسیده است."
                ),
                None,
            )

        # ----------------------------------------------------
        # Upgrade Cost
        # ----------------------------------------------------

        cost = get_upgrade_cost(
            current_level
        )

        if cost is None:

            return (
                False,
                "❌ هزینه ارتقای این Level تعریف نشده است.",
                None,
            )

        xp_cost = cost["xp"]
        gold_cost = cost["gold"]

        # ----------------------------------------------------
        # Current / Next Power
        # ----------------------------------------------------

        current_power = get_skill_power(
            skill,
            current_level,
        )

        next_power = get_skill_power(
            skill,
            current_level + 1,
        )

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        info = {
            "skill_id": skill.id,
            "skill_name": skill.name,

            "current_level": current_level,
            "next_level": current_level + 1,
            "max_level": skill.max_level,

            "current_power": current_power,
            "next_power": next_power,

            "xp_cost": xp_cost,
            "gold_cost": gold_cost,

            "current_xp": character.skill_xp,
            "current_gold": character.gold,

            "can_upgrade": (
                character.skill_xp >= xp_cost
                and character.gold >= gold_cost
            ),
        }

        return (
            True,
            "OK",
            info,
        )


# ============================================================
# Upgrade Skill
# ============================================================

async def upgrade_skill(
    telegram_id: int,
    skill_id: int,
) -> tuple[bool, str]:

    async with AsyncSessionLocal() as session:

        # ----------------------------------------------------
        # Character
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Skill
        # ----------------------------------------------------

        result = await session.execute(
            select(
                CharacterSkill,
                Skill,
            )
            .join(
                Skill,
                Skill.id == CharacterSkill.skill_id,
            )
            .where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == skill_id,
                CharacterSkill.unlocked.is_(True),
                Skill.is_active.is_(True),
            )
        )

        row = result.first()

        if row is None:
            return (
                False,
                "❌ این مهارت را یاد نگرفته‌ای.",
            )

        character_skill, skill = row

        current_level = character_skill.level

        # ----------------------------------------------------
        # Max Level
        # ----------------------------------------------------

        if current_level >= skill.max_level:
            return (
                False,
                (
                    f"🔮 مهارت «{skill.name}» "
                    f"به حداکثر Level {skill.max_level} رسیده است."
                ),
            )

        # ----------------------------------------------------
        # Cost
        # ----------------------------------------------------

        cost = get_upgrade_cost(
            current_level
        )

        if cost is None:
            return (
                False,
                "❌ هزینه ارتقای این Level تعریف نشده است.",
            )

        xp_cost = cost["xp"]
        gold_cost = cost["gold"]

        # ----------------------------------------------------
        # Resource Check
        # ----------------------------------------------------

        if character.skill_xp < xp_cost:
            return (
                False,
                (
                    "🔮 Skill XP کافی نیست.\n\n"
                    f"نیاز: {xp_cost:,}\n"
                    f"موجودی: {character.skill_xp:,}"
                ),
            )

        if character.gold < gold_cost:
            return (
                False,
                (
                    "💰 Gold کافی نیست.\n\n"
                    f"نیاز: {gold_cost:,}\n"
                    f"موجودی: {character.gold:,}"
                ),
            )

        # ----------------------------------------------------
        # Upgrade
        # ----------------------------------------------------

        character.skill_xp -= xp_cost
        character.gold -= gold_cost

        character_skill.level += 1

        await session.commit()

        return (
            True,
            (
                "🎉 <b>ارتقای مهارت موفق بود!</b>\n\n"
                f"🔮 {skill.name}\n"
                f"📈 Level جدید: {character_skill.level}\n\n"
                f"🔮 Skill XP مصرف‌شده: {xp_cost:,}\n"
                f"💰 Gold مصرف‌شده: {gold_cost:,}"
            ),
        )


# ============================================================
# Skill Details
# ============================================================

async def get_skill_details(
    character_id: int,
    skill_id: int,
) -> dict | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(
                Skill,
                CharacterSkill,
            )
            .outerjoin(
                CharacterSkill,
                (
                    (CharacterSkill.skill_id == Skill.id)
                    &
                    (
                        CharacterSkill.character_id
                        == character_id
                    )
                ),
            )
            .where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        row = result.first()

        if row is None:
            return None

        skill, character_skill = row

        learned = (
            character_skill is not None
            and character_skill.unlocked
        )

        level = (
            character_skill.level
            if learned
            else 1
        )

        return {
            "skill": skill,
            "character_skill": character_skill,
            "learned": learned,
            "level": level,
            "power": get_skill_power(
                skill,
                level,
            ),
            "mana_cost": get_skill_mana_cost(
                skill,
                level,
            ),
        }


# ============================================================
# Compatibility API
# ============================================================

async def get_upgrade_info(
    telegram_id: int,
    skill_id: int,
) -> tuple[bool, str, dict | None]:

    return await get_skill_upgrade_info(
        telegram_id,
        skill_id,
    )