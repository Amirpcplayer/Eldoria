from __future__ import annotations

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.social_systems import PlayerSetting
from models.world_systems import CharacterActivity, NotificationEvent
from datetime import datetime
from services.title_service import sync_unlocked_titles


MAX_CHARACTER_LEVEL = 100


# ============================================================
# XP CURVE
# ============================================================

def get_required_xp(level: int) -> int:
    """
    XP موردنیاز برای رفتن از Level فعلی به Level بعدی.

    رشد XP به‌صورت تدریجی افزایش پیدا می‌کند
    تا Levelهای بالا نیازمند XP بیشتری باشند.
    """

    if level >= MAX_CHARACTER_LEVEL:
        return 0

    # Level 1 -> 100
    # Level 2 -> 130
    # Level 3 -> 165
    # Level 4 -> 205
    # ...
    return int(
        100
        * (level ** 1.35)
    )


# ============================================================
# BASE CHARACTER STATS
# ============================================================

BASE_STATS = {
    "max_hp": 100,
    "max_mana": 100,
    "attack": 10,
    "magic_power": 10,
    "defense": 10,
    "magic_defense": 10,
    "speed": 10,
    "accuracy": 10,
    "luck": 10,
    "critical": 5,
}


# ============================================================
# LEVEL POWER CURVE
# ============================================================

def get_base_stats_for_level(
    level: int,
) -> dict[str, int]:
    """Endgame-scaled base stats shared by XP gifts and normal level-ups."""
    level = max(1, min(level, MAX_CHARACTER_LEVEL))
    growth = (level - 1) ** 2
    return {
        "max_hp": 100 + 50 * growth,
        "max_mana": 100 + 50 * growth,
        "attack": 10 + int(5.1 * growth),
        "magic_power": 10 + int(5.1 * growth),
        "defense": 8 + int(2.55 * growth),
        "magic_defense": 8 + int(2.55 * growth),
        "speed": 10 + int(0.35 * growth),
        "accuracy": 10 + int(0.35 * growth),
        "luck": 5 + int(0.08 * growth),
        "critical": min(75, 5 + int(0.08 * growth)),
    }


# ============================================================
# APPLY LEVEL STATS
# ============================================================

def apply_level_stats(
    character: Character,
) -> None:
    """
    Stats پایه Character را بر اساس Level فعلی
    هماهنگ می‌کند.

    Equipment در این مرحله اعمال نمی‌شود.
    Equipment بعداً هنگام محاسبه Final Stats اضافه می‌شود.
    """

    stats = get_base_stats_for_level(
        character.level
    )

    character.max_hp = stats["max_hp"]
    character.max_mana = stats["max_mana"]

    character.attack = stats["attack"]
    character.magic_power = stats["magic_power"]

    character.defense = stats["defense"]
    character.magic_defense = stats["magic_defense"]

    character.speed = stats["speed"]
    character.accuracy = stats["accuracy"]
    character.luck = stats["luck"]
    character.critical = stats["critical"]

    # بعد از Level Up، HP و Mana کامل می‌شوند.
    character.hp = character.max_hp
    character.mana = character.max_mana


# ============================================================
# CHARACTER XP
# ============================================================

async def add_character_xp(
    telegram_id: int,
    amount: int,
    apply_scroll_bonus: bool = True,
) -> tuple[bool, int, int, int]:

    if amount <= 0:
        return False, 0, 0, 0

    # Apply the strongest active XP-reward scroll. Direct XP granted by
    # consuming an XP scroll itself is excluded to avoid multiplying twice.
    if apply_scroll_bonus:
        try:
            from services.scroll_service import get_buff
            multipliers = []
            for kind in ("experience", "experience_small", "explorer"):
                buff = await get_buff(telegram_id, kind)
                if buff:
                    multipliers.append(float(buff.get("xp_multiplier", 1.0)))
            if multipliers:
                amount = max(amount, int(amount * max(multipliers)))
        except Exception:
            # XP must still be awarded if Redis/buff lookup is temporarily down.
            pass

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return False, 0, 0, 0

        # ----------------------------------------------------
        # MAX LEVEL
        # ----------------------------------------------------

        if character.level >= MAX_CHARACTER_LEVEL:

            character.level = MAX_CHARACTER_LEVEL
            character.xp = 0

            apply_level_stats(character)
            sync_unlocked_titles(character)

            await session.commit()

            return (
                True,
                character.xp,
                character.level,
                0,
            )

        # ----------------------------------------------------
        # ADD XP
        # ----------------------------------------------------

        character.xp += amount

        levels_gained = 0

        # ----------------------------------------------------
        # LEVEL UP LOOP
        # ----------------------------------------------------

        while character.level < MAX_CHARACTER_LEVEL:

            required_xp = get_required_xp(
                character.level
            )

            if required_xp <= 0:
                break

            if character.xp < required_xp:
                break

            character.xp -= required_xp

            character.level += 1

            levels_gained += 1

            # اعمال قدرت Level جدید
            apply_level_stats(character)

        # ----------------------------------------------------
        # SAFETY SYNC
        # ----------------------------------------------------

        if levels_gained == 0:

            expected = get_base_stats_for_level(
                character.level
            )

            # اگر قهرمان از قبل Level بالاتر داشته
            # ولی Stats آن هنوز قدیمی هستند،
            # فقط Base Stats را اصلاح می‌کنیم.
            if (
                character.max_hp < expected["max_hp"]
                or character.max_mana < expected["max_mana"]
                or character.attack < expected["attack"]
                or character.magic_power < expected["magic_power"]
                or character.defense < expected["defense"]
                or character.magic_defense < expected["magic_defense"]
                or character.speed < expected["speed"]
                or character.accuracy < expected["accuracy"]
                or character.luck < expected["luck"]
                or character.critical < expected["critical"]
            ):

                old_hp_ratio = (
                    character.hp / character.max_hp
                    if character.max_hp > 0
                    else 1.0
                )

                old_mana_ratio = (
                    character.mana / character.max_mana
                    if character.max_mana > 0
                    else 1.0
                )

                character.max_hp = expected["max_hp"]
                character.max_mana = expected["max_mana"]

                character.attack = expected["attack"]
                character.magic_power = expected["magic_power"]

                character.defense = expected["defense"]
                character.magic_defense = expected["magic_defense"]

                character.speed = expected["speed"]
                character.accuracy = expected["accuracy"]
                character.luck = expected["luck"]
                character.critical = expected["critical"]

                character.hp = max(
                    1,
                    min(
                        character.max_hp,
                        int(
                            character.max_hp
                            * old_hp_ratio
                        ),
                    ),
                )

                character.mana = max(
                    0,
                    min(
                        character.max_mana,
                        int(
                            character.max_mana
                            * old_mana_ratio
                        ),
                    ),
                )

        # ----------------------------------------------------
        # MAX LEVEL
        # ----------------------------------------------------

        if character.level >= MAX_CHARACTER_LEVEL:
            character.xp = 0

        sync_unlocked_titles(character)
        if levels_gained > 0:
            session.add(CharacterActivity(character_id=character.id,event_type="level_up",details=f"level={character.level};levels_gained={levels_gained}"))
            setting = await session.scalar(select(PlayerSetting).where(PlayerSetting.telegram_id == telegram_id))
            if setting is None or setting.notifications:
                session.add(NotificationEvent(telegram_id=telegram_id,event_type="level_up",message=f"🎉 قهرمانت به سطح {character.level} رسید و لقب سطح جدید را باز کرد!",delivered=False))

        await session.commit()

        return (
            True,
            character.xp,
            character.level,
            levels_gained,
        )


# ============================================================
# SKILL XP
# ============================================================

async def add_skill_xp(
    telegram_id: int,
    amount: int,
) -> tuple[bool, int]:

    if amount <= 0:
        return False, 0

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return False, 0

        character.skill_xp += amount

        await session.commit()

        return (
            True,
            character.skill_xp,
        )