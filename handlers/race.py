from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.database import AsyncSessionLocal
from models.character import Character
from keyboards.main_menu import enter_game_keyboard
from game.stats import get_base_stats


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


@router.callback_query(
    lambda callback: callback.data.startswith("race:")
)
async def race_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    race_id = callback.data.split(":")[1]

    race_name = RACE_NAMES.get(race_id)

    if race_name is None:
        await callback.answer(
            "❌ نژاد نامعتبر است.",
            show_alert=True,
        )
        return

    data = await state.get_data()

    name = data.get("name")

    if not name:
        await callback.answer(
            "❌ اطلاعات ساخت شخصیت ناقص است.",
            show_alert=True,
        )
        await state.clear()
        return

    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:

        # بررسی اینکه این اکانت قبلاً شخصیت ساخته یا نه
        existing_character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if existing_character:
            await callback.message.edit_text(
                "⚠️ تو قبلاً یک قهرمان ساخته‌ای!\n\n"
                f"👤 نام: {existing_character.name}\n"
                f"🧬 نژاد: "
                f"{RACE_NAMES.get(existing_character.race, existing_character.race)}\n\n"
                "❌ امکان ساخت قهرمان دوم وجود ندارد."
            )

            await state.clear()
            await callback.answer()
            return

        # دریافت Stats پایه نژاد
        stats = get_base_stats(race_id)

        # ساخت شخصیت
        character = Character(
            telegram_id=telegram_id,
            name=name,
            race=race_id,

            hp=stats["hp"],
            max_hp=stats["hp"],

            mana=stats["mana"],
            max_mana=stats["mana"],

            attack=stats["attack"],
            magic_power=stats["magic_power"],
            defense=stats["defense"],
            magic_defense=stats["magic_defense"],
            speed=stats["speed"],
            accuracy=stats["accuracy"],
            luck=stats["luck"],
            critical=stats["critical"],
        )

        session.add(character)

        try:
            await session.commit()

        except IntegrityError:
            await session.rollback()

            await callback.message.edit_text(
                "❌ این نام قهرمان قبلاً توسط بازیکن دیگری انتخاب شده است.\n\n"
                "لطفاً با /start دوباره یک نام دیگر انتخاب کن."
            )

            await state.clear()
            await callback.answer()
            return

    await callback.message.edit_text(
        "🎉 <b>ساخت قهرمان کامل شد!</b>\n\n"
        f"👤 نام: {name}\n"
        f"🧬 نژاد: {RACE_NAMES.get(race_id, race_id)}\n\n"
        f"⭐ Level: {character.level}\n"
        f"💫 XP: {character.xp}\n\n"
        f"❤️ HP: {character.hp}/{character.max_hp}\n"
        f"💠 Mana: {character.mana}/{character.max_mana}\n\n"
        f"⚔️ Attack: {character.attack}\n"
        f"🔮 Magic Power: {character.magic_power}\n"
        f"🛡️ Defense: {character.defense}\n"
        f"🔰 Magic Defense: {character.magic_defense}\n"
        f"⚡ Speed: {character.speed}\n"
        f"🎯 Accuracy: {character.accuracy}\n"
        f"🍀 Luck: {character.luck}\n"
        f"💥 Critical: {character.critical}%\n\n"
        f"💰 Gold: {character.gold}\n"
        f"💎 Gems: {character.gems}\n\n"
        "⚔️ ماجراجویی تو در اِلدوریا آغاز شد!\n\n"
        "👇 برای شروع بازی روی دکمه زیر بزن:",
        reply_markup=enter_game_keyboard(),
    )

    await state.clear()
    await callback.answer()