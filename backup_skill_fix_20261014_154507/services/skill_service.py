from sqlalchemy import select

from database.database import AsyncSessionLocal

from models.character import Character
from models.character_skill import CharacterSkill
from models.skill import Skill

from services.quest_service import record_skill_learned


# ============================================================
# Skill Configuration
# ============================================================

SKILL_MANA_GROWTH: dict[str, int] = {
    "fire": 8,
    "water": 8,
    "wind": 9,
    "earth": 10,
    "electro": 12,
    "ice": 13,
    "light": 18,
    "dark": 20,
}


# Cost to upgrade:
# current level -> next level
SKILL_UPGRADE_COSTS: dict[int, dict[str, int]] = {
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
    Calculate skill power for a given level.

    Formula:
        base_power + ((level - 1) * power_per_level)
    """

    level = max(1, level)

    # At Lv.200, the skill's own contribution is about 15k. Combat adds
    # 70% of the hero's magic stat, bringing a typical max-level cast near
    # 50k before elemental weakness; this avoids an unintended 80k+ baseline.
    # Normalize older DB values without requiring a destructive skill reseed.
    per_level = max(75, int(skill.power_per_level or 0) * 0.65)
    return int(skill.base_power or 0) + ((level - 1) * per_level)


def get_skill_mana_cost(
    skill: Skill,
    level: int,
) -> int:
    """
    Calculate mana cost for a given skill level.

    Formula:
        base mana cost + ((level - 1) * element mana growth)
    """

    level = max(1, level)

    growth = SKILL_MANA_GROWTH.get(skill.element, 0)
    # Costs grow gradually, not linearly into impossible values at Lv.200.
    return int(skill.mana_cost or 0) + int((level - 1) * growth * 0.35)


def get_upgrade_cost(
    current_level: int,
) -> dict[str, int] | None:
    """
    Return the upgrade cost for:
        current_level -> current_level + 1
    """

    if current_level in SKILL_UPGRADE_COSTS:
        return SKILL_UPGRADE_COSTS[current_level]
    if 10 <= current_level < 200:
        # Increasing endgame costs, still allowing progression with skill XP.
        steps = current_level - 9
        return {"xp": 16000 + steps * 5000, "gold": 32000 + steps * 10000}
    return None


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
    Skill slot progression:

    Level 1-19  -> 1 slot
    Level 20-59 -> 2 slots
    Level 60+   -> 3 slots
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
            list(
                result.scalars().all()
            )
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

    return character_level >= skill.unlock_level


async def can_learn_skill(
    character_id: int,
    skill_id: int,
) -> tuple[bool, str]:

    async with AsyncSessionLocal() as session:

        # ----------------------------------------------------
        # Character
        # ----------------------------------------------------

        character = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        if character is None:
            return (
                False,
                "شخصیت پیدا نشد.",
            )

        # ----------------------------------------------------
        # Skill
        # ----------------------------------------------------

        skill = await session.scalar(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        if skill is None:
            return (
                False,
                "این مهارت پیدا نشد.",
            )

        # ----------------------------------------------------
        # Existing Character Skill
        # ----------------------------------------------------

        existing = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill_id,
            )
        )

        if existing is not None and existing.unlocked:
            return (
                False,
                "این مهارت را قبلاً یاد گرفته‌اید.",
            )

        # ----------------------------------------------------
        # Level Check
        # ----------------------------------------------------

        if not is_skill_unlocked_by_level(
            character.level,
            skill,
        ):
            return (
                False,
                (
                    "🔒 این مهارت هنوز برای شما باز نشده است.\n\n"
                    f"سطح فعلی: {character.level}\n"
                    f"سطح موردنیاز: {skill.unlock_level}"
                ),
            )

        # ----------------------------------------------------
        # Slot Check
        # ----------------------------------------------------

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
                    "🔒 تمام اسلات‌های مهارت شما پر شده‌اند.\n\n"
                    f"اسلات‌ها: {used_slots}/{max_slots}"
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
                "شخصیت پیدا نشد.",
            )

        # ----------------------------------------------------
        # Skill
        # ----------------------------------------------------

        skill = await session.scalar(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        if skill is None:
            return (
                False,
                "این مهارت پیدا نشد.",
            )

        # ----------------------------------------------------
        # Existing Skill
        # ----------------------------------------------------

        existing = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == skill_id,
            )
        )

        if existing is not None and existing.unlocked:
            return (
                False,
                "این مهارت را قبلاً یاد گرفته‌اید.",
            )

        # ----------------------------------------------------
        # Level Check
        # ----------------------------------------------------

        if not is_skill_unlocked_by_level(
            character.level,
            skill,
        ):
            return (
                False,
                (
                    "🔒 این مهارت هنوز برای شما باز نشده است.\n\n"
                    f"سطح فعلی: {character.level}\n"
                    f"سطح موردنیاز: {skill.unlock_level}"
                ),
            )

        # ----------------------------------------------------
        # Available Slots
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
                    "🔒 تمام اسلات‌های مهارت شما پر شده‌اند.\n\n"
                    f"اسلات‌ها: {len(used_skills)}/{max_slots}"
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
                "اسلات خالی برای یادگیری این مهارت وجود ندارد.",
            )

        # ----------------------------------------------------
        # Create / Restore Character Skill
        # ----------------------------------------------------

        if existing is None:
            character_skill = CharacterSkill(
                character_id=character.id,
                skill_id=skill.id,
                level=1,
                slot=free_slot,
                unlocked=True,
            )

            session.add(character_skill)

        else:
            existing.level = 1
            existing.slot = free_slot
            existing.unlocked = True
            character_skill = existing

        # ----------------------------------------------------
        # Commit Skill Unlock
        # ----------------------------------------------------

        await session.commit()

        # ----------------------------------------------------
        # Quest Progress
        #
        # Quest progress must not undo a successfully learned
        # skill if quest tracking happens to fail.
        # ----------------------------------------------------

        try:
            await record_skill_learned(
                telegram_id=telegram_id,
                skill_id=skill_id,
            )
        except Exception:
            pass

        return (
            True,
            (
                "🎉 مهارت با موفقیت یاد گرفته شد!\n\n"
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
                "شخصیت پیدا نشد.",
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
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        row = result.first()

        if row is None:
            return (
                False,
                "این مهارت را یاد نگرفته‌اید.",
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
                "هزینه ارتقای این سطح تعریف نشده است.",
                None,
            )

        xp_cost = cost["xp"]
        gold_cost = cost["gold"]

        # ----------------------------------------------------
        # Current / Next Stats
        # ----------------------------------------------------

        next_level = current_level + 1

        current_power = get_skill_power(
            skill,
            current_level,
        )

        next_power = get_skill_power(
            skill,
            next_level,
        )

        current_mana = get_skill_mana_cost(
            skill,
            current_level,
        )

        next_mana = get_skill_mana_cost(
            skill,
            next_level,
        )

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        info = {
            "skill_id": skill.id,
            "skill_name": skill.name,

            "current_level": current_level,
            "next_level": next_level,
            "max_level": skill.max_level,

            "current_power": current_power,
            "next_power": next_power,

            "current_mana": current_mana,
            "next_mana": next_mana,

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
                "شخصیت پیدا نشد.",
            )

        # ----------------------------------------------------
        # Skill + Character Skill
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
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        row = result.first()

        if row is None:
            return (
                False,
                "این مهارت را یاد نگرفته‌اید.",
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
                "هزینه ارتقای این سطح تعریف نشده است.",
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

        new_level = character_skill.level

        await session.commit()

        return (
            True,
            (
                "🎉 ارتقای مهارت موفق بود!\n\n"
                f"🔮 {skill.name}\n"
                f"📈 Level جدید: {new_level}\n\n"
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
                    & (
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