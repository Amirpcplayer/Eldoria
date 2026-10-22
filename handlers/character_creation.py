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


router = Router()

GENDER_NAMES = {"male": "مرد", "female": "زن"}


@router.message(CharacterCreation.waiting_for_name)
async def character_name_handler(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ نام قهرمان را به‌صورت متنی وارد کن.")
        return

    name = message.text.strip()
    # Prevent Telegram commands from being registered as hero names.
    if name.startswith("/") or name.startswith("!"):
        await message.answer(
            "❌ نام قهرمان نمی‌تواند شبیه دستور ربات باشد. فقط یک نام معمولی وارد کن."
        )
        return
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
        "༺ 📜 پیمان سرنوشت 📜 ༻\n\n"
        f"✅ نام قهرمان در دفتر کهن ثبت شد: <b>{escape(name)}</b>\n\n"
        "اما پیش از آن‌که قدم در مسیر قدرت بگذاری، باید هویت قهرمانت را آشکار کنی.\n\n"
        "⚔️ انتخاب تو، بخشی از داستانی خواهد بود که در اِلدوریا رقم می‌زنی.\n\n"
        "⚧ <b>جنسیت قهرمانت را انتخاب کن:</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✦ سرنوشت هنوز نوشته نشده است ✦",
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
    new_panel = await callback.message.answer(
        "༺ 🧬 میراث نیاکان 🧬 ༻\n\n"
        f"✅ جنسیت قهرمان: <b>{gender_name}</b>\n\n"
        "در اعماق اِلدوریا، خون نیاکان هنوز قدرتی فراموش‌نشده در خود دارد. هر نژاد، ریشه‌ای متفاوت و داستانی ویژه دارد.\n\n"
        "🌑 انتخاب تو، نخستین گام در شکل‌گیری هویت قهرمانت خواهد بود.\n\n"
        "🧬 <b>نژاد قهرمانت را انتخاب کن:</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✦ میراثت را برگزین، قهرمان ✦",
        reply_markup=race_keyboard(),
        parse_mode=ParseMode.HTML,
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()
