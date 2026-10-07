from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from states.character import CharacterCreation
from keyboards.character import race_keyboard


router = Router()


@router.message(CharacterCreation.waiting_for_name)
async def character_name_handler(
    message: Message,
    state: FSMContext,
):

    if not message.text:
        await message.answer(
            "❌ لطفاً نام قهرمانت را به صورت متنی ارسال کن."
        )
        return

    name = message.text.strip()

    # بررسی حداقل طول نام
    if len(name) < 3:
        await message.answer(
            "❌ نام قهرمان باید حداقل ۳ حرف داشته باشد.\n\n"
            "✍️ لطفاً یک نام مناسب وارد کن:"
        )
        return

    # بررسی حداکثر طول نام
    if len(name) > 32:
        await message.answer(
            "❌ نام قهرمان نمی‌تواند بیشتر از ۳۲ حرف باشد.\n\n"
            "✍️ لطفاً یک نام کوتاه‌تر وارد کن:"
        )
        return

    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:

        # بررسی اینکه همین اکانت قبلاً شخصیت ساخته یا نه
        existing_player = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if existing_player:
            await message.answer(
                "⚠️ تو قبلاً یک قهرمان ساخته‌ای!\n\n"
                f"👤 نام قهرمان: {existing_player.name}\n"
                f"🧬 نژاد: {existing_player.race}\n\n"
                "❌ امکان ساخت قهرمان دوم وجود ندارد."
            )
            await state.clear()
            return

        # بررسی اینکه نام توسط بازیکن دیگری استفاده شده یا نه
        existing_name = await session.scalar(
            select(Character).where(
                Character.name == name
            )
        )

        if existing_name:
            await message.answer(
                "❌ این نام قبلاً توسط یک بازیکن دیگر انتخاب شده است.\n\n"
                f"👤 نام وارد شده: {name}\n\n"
                "✍️ لطفاً یک نام دیگر انتخاب کن:"
            )
            return

    # ذخیره نام برای مرحله انتخاب نژاد
    await state.update_data(name=name)

    await message.answer(
        f"✅ نام قهرمان ثبت شد: {name}\n\n"
        "🧬 حالا نژاد قهرمانت را انتخاب کن.",
        reply_markup=race_keyboard(),
    )