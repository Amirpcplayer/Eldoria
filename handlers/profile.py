from aiogram import Router, F
from aiogram.types import CallbackQuery

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.skill import Skill
from models.character_skill import CharacterSkill

from keyboards.profile import profile_keyboard

from services.profile_service import (
    get_rank,
    get_title,
    get_xp_progress,
    create_xp_bar,
    get_combat_power,
)


router = Router()


RACE_NAMES = {
    "human": "👤 انسان",
    "elf": "🧝 الف",
    "demon": "😈 شیطان",
    "dwarf": "⛏️ دورف",
    "dragonite": "🐉 درگونایت",
    "fairy": "🧚 پری",
    "vampire": "🧛 خون‌آشام",
    "werewolf": "🐺 گرگینه",
}


async def get_character(
    telegram_id: int,
):
    async with AsyncSessionLocal() as session:

        return await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )


async def get_learned_skills(
    character_id: int,
):
    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Skill, CharacterSkill)
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
                Skill.id.asc()
            )
        )

        return result.all()


def format_skills(
    learned_skills,
) -> str:

    if not learned_skills:
        return (
            "✨ **جادوهای آموخته‌شده**\n"
            "هنوز هیچ جادویی یاد نگرفته‌ای.\n"
        )

    text = "✨ **جادوهای آموخته‌شده**\n"

    for skill, character_skill in learned_skills:

        text += (
            f"• {skill.name} — "
            f"Level **{character_skill.level}**\n"
        )

    return text


def format_profile(
    character: Character,
    learned_skills,
) -> str:

    rank = get_rank(
        character.level
    )

    title = get_title(
        character.level
    )

    current_xp, required_xp, xp_percent = (
        get_xp_progress(
            character.level,
            character.xp,
        )
    )

    xp_bar = create_xp_bar(
        xp_percent
    )

    combat_power = get_combat_power(
        character
    )

    race = RACE_NAMES.get(
        character.race,
        character.race or "نامشخص",
    )

    if character.level >= 100:

        xp_text = "MAX"

    else:

        xp_text = (
            f"{current_xp:,} / "
            f"{required_xp:,}"
        )

    skills_text = format_skills(
        learned_skills
    )

    return (
        "👤 **پروفایل قهرمان**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"🧑 نام: **{character.name}**\n"
        f"🧬 نژاد: {race}\n"
        f"🏅 Rank: **{rank}**\n"
        f"🎖️ عنوان: **{title}**\n\n"

        "📈 **پیشرفت قهرمان**\n"
        f"⭐ Level: **{character.level}**\n"
        f"🧪 XP: **{xp_text}**\n"
        f"{xp_bar} {xp_percent}%\n\n"

        "❤️ **سلامتی**\n"
        f"❤️ HP: **{character.hp:,} / "
        f"{character.max_hp:,}**\n"
        f"💧 Mana: **{character.mana:,} / "
        f"{character.max_mana:,}**\n\n"

        "⚔️ **قدرت‌های رزمی**\n"
        f"⚔️ Attack: **{character.attack}**\n"
        f"🔮 Magic Power: **{character.magic_power}**\n"
        f"🛡️ Defense: **{character.defense}**\n"
        f"🔰 Magic Defense: **{character.magic_defense}**\n"
        f"💨 Speed: **{character.speed}**\n"
        f"🎯 Accuracy: **{character.accuracy}**\n\n"

        "🍀 **ویژگی‌های ویژه**\n"
        f"🍀 Luck: **{character.luck}**\n"
        f"💥 Critical: **{character.critical}%**\n\n"

        f"{skills_text}\n"

        "💰 **دارایی‌ها**\n"
        f"💰 Gold: **{character.gold:,}**\n"
        f"💎 Gems: **{character.gems:,}**\n\n"

        "⚡ **قدرت رزمی**\n"
        f"🔥 Combat Power: **{combat_power:,}**\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🌌 قهرمانت در سرزمین اِلدوریا آماده ماجراجویی است!"
    )


@router.callback_query(
    F.data == "menu:profile"
)
async def profile_handler(
    callback: CallbackQuery,
):

    character = await get_character(
        callback.from_user.id
    )

    if character is None:

        await callback.answer(
            "🌫️ قهرمانت پیدا نشد.",
            show_alert=True,
        )
        return

    learned_skills = await get_learned_skills(
        character.id
    )

    await callback.message.edit_text(
        format_profile(
            character,
            learned_skills,
        ),
        reply_markup=profile_keyboard(),
        parse_mode="Markdown",
    )

    await callback.answer()


@router.callback_query(
    F.data == "profile:stats"
)
async def profile_stats_handler(
    callback: CallbackQuery,
):

    character = await get_character(
        callback.from_user.id
    )

    if character is None:

        await callback.answer(
            "🌫️ قهرمانت پیدا نشد.",
            show_alert=True,
        )
        return

    rank = get_rank(
        character.level
    )

    title = get_title(
        character.level
    )

    combat_power = get_combat_power(
        character
    )

    race = RACE_NAMES.get(
        character.race,
        character.race or "نامشخص",
    )

    learned_skills = await get_learned_skills(
        character.id
    )

    skills_text = format_skills(
        learned_skills
    )

    await callback.message.edit_text(
        "📊 **آمار کامل قهرمان**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 نام: **{character.name}**\n"
        f"🧬 نژاد: {race}\n"
        f"🏅 Rank: **{rank}**\n"
        f"🎖️ عنوان: **{title}**\n\n"

        "❤️ **Vital Stats**\n"
        f"❤️ HP: **{character.hp:,} / "
        f"{character.max_hp:,}**\n"
        f"💧 Mana: **{character.mana:,} / "
        f"{character.max_mana:,}**\n\n"

        "⚔️ **Offensive Stats**\n"
        f"⚔️ Attack: **{character.attack}**\n"
        f"🔮 Magic Power: **{character.magic_power}**\n"
        f"🎯 Accuracy: **{character.accuracy}**\n"
        f"💥 Critical Chance: **{character.critical}%**\n\n"

        "🛡️ **Defensive Stats**\n"
        f"🛡️ Defense: **{character.defense}**\n"
        f"🔰 Magic Defense: **{character.magic_defense}**\n\n"

        "🌟 **Utility Stats**\n"
        f"💨 Speed: **{character.speed}**\n"
        f"🍀 Luck: **{character.luck}**\n\n"

        f"{skills_text}\n"

        "⚡ **Combat Power**\n"
        f"🔥 **{combat_power:,}**\n\n"

        "━━━━━━━━━━━━━━━━━━",
        reply_markup=profile_keyboard(),
        parse_mode="Markdown",
    )

    await callback.answer()