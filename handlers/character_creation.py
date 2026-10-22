from html import escape

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from states.character import CharacterCreation
from keyboards.character import gender_keyboard, race_keyboard
from services.panel_image_service import replace_panel_with_text


router = Router()

GENDER_NAMES = {"male": "مرد", "female": "زن"}


@router.message(CharacterCreation.waiting_for_name)
async def character_name_handler(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ نام قهرمان را به‌صورت متنی وارد کن.")
        return

    name = message.text.strip()
    if len(name) < 3:
        await message.answer(
            "༺ 📜 نامی برای افسانه‌ات برگزین 📜 ༻\n\n"
            "نام قهرمان باید دست‌کم ۳ حرف داشته باشد.\n\n"
            "✍️ نام دیگری وارد کن:"
        )
        return
    if len(name) > 32:
        await message.answer(
            "༺ 📜 نام قهرمان 📜 ༻\n\n"
            "نام قهرمان نمی‌تواند بیشتر از ۳۲ حرف باشد.\n\n"
            "✍️ نام کوتاه‌تری وارد کن:"
        )
        return

    telegram_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        existing_player = await session.scalar(
            select(Character).where(Character.telegram_id == telegram_id)
        )
        if existing_player:
            await message.answer(
                "༺ ⚠️ سرنوشت از پیش نوشته شده است ⚠️ ༻\n\n"
                f"👤 قهرمان ثبت‌شده: {escape(existing_player.name)}\n"
                "برای هر حساب، تنها یک قهرمان قابل ساخت است."
            )
            await state.clear()
            return

        existing_name = await session.scalar(
            select(Character).where(Character.name == name)
        )
        if existing_name:
            await message.answer(
                "༺ 🕯️ این نام پیش‌تر ثبت شده است 🕯️ ༻\n\n"
                f"👤 نام انتخابی: {escape(name)}\n\n"
                "نام دیگری برگزین تا افسانه‌ات با هویت یگانه‌ای آغاز شود.\n"
                "✍️ نام تازه را وارد کن:"
            )
            return

    await state.update_data(name=name)
    await state.set_state(CharacterCreation.waiting_for_gender)
    await message.answer(
        f"👤 نام قهرمان: <b>{escape(name)}</b>\n\n⚧ جنسیت قهرمانت را انتخاب کن:",
        reply_markup=gender_keyboard(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(CharacterCreation.waiting_for_gender, lambda c: c.data and c.data.startswith("gender:"))
async def character_gender_handler(callback: CallbackQuery, state: FSMContext):
    gender_id = callback.data.split(":", 1)[1]
    gender_name = GENDER_NAMES.get(gender_id)
    data = await state.get_data()
    name = data.get("name")

    if gender_name is None or not name:
        await callback.answer("اطلاعات ساخت قهرمان ناقص است؛ دوباره /start را بزن.", show_alert=True)
        await state.clear()
        return

    await state.update_data(gender=gender_id)
    await replace_panel_with_text(
        callback=callback,
        text=f"⚧ جنسیت: <b>{gender_name}</b>\\n\\n🧬 نژاد قهرمانت را انتخاب کن:",
        reply_markup=race_keyboard(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()
