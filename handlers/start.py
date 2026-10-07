from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from states.character import CharacterCreation
from keyboards.main_menu import main_menu_keyboard


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


@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
):

    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

    # پلیر قبلاً شخصیت ساخته است
    if character:

        await state.clear()

        race = RACE_NAMES.get(
            character.race,
            character.race or "نامشخص",
        )

        await message.answer(
            f"🌌 به اِلدوریا خوش آمدی، {character.name}!\n\n"
            "⚔️ قهرمانت آماده است تا به ماجراجویی ادامه دهد.\n\n"
            f"👤 قهرمان: {character.name}\n"
            f"🧬 نژاد: {race}\n\n"
            "🎮 منوی اصلی:",
            reply_markup=main_menu_keyboard(),
        )

        return

    # پلیر هنوز شخصیت ندارد
    await state.set_state(
        CharacterCreation.waiting_for_name
    )

    await message.answer(
        "🌌 به اِلدوریا خوش آمدید!\n\n"
        "⚔️ سفر افسانه‌ای تو از همین‌جا آغاز می‌شود.\n\n"
        "🧙 برای ساخت شخصیت، ابتدا نام قهرمانت را وارد کن.\n\n"
        "✍️ نام قهرمانت را بفرست:"
    )