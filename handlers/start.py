from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from states.character import CharacterCreation
from services.panel_image_service import send_panel
from services.vitals_recovery_service import recover_character_vitals
from handlers.admin_temp import admin_keyboard, is_admin


router = Router()


MAIN_MENU_TEXT = (
    "🎮 <b>منوی اصلی اِلدوریا</b>\n\n"
    "🌌 ماجراجویی تو در اِلدوریا ادامه دارد..."
)


@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
    command: CommandObject,
):
    if message.from_user is None:
        return

    telegram_id = message.from_user.id

    # Open the admin panel immediately from the private deep link.
    if command.args == "admin":
        if message.chat.type != "private":
            return
        if not is_admin(telegram_id):
            await message.answer("⛔ شما دسترسی ادمین ندارید.")
            return
        await state.clear()
        await message.answer(
            "🛡 پنل مدیریت World Eldoria\n\nبخش موردنظرت را انتخاب کن:",
            reply_markup=admin_keyboard(),
        )
        return

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == telegram_id)
        )

    if character:
        await recover_character_vitals(telegram_id)
        await state.clear()
        await message.answer(
            "༺ 🌑 بازگشت به اِلدوریا 🌑 ༻\n\n"
            f"قهرمان <b>{character.name}</b>، سرنوشتت هنوز در انتظار توست.\n\n"
            "برای مشاهدهٔ وضعیت قهرمانت از /profile استفاده کن."
        )
        return

    if message.chat.type != "private":
        bot_username = (await message.bot.get_me()).username
        if bot_username:
            await message.answer(
                "برای ساخت قهرمان، در گفت‌وگوی خصوصی ربات دستور /start را بزن.\n"
                f"https://t.me/{bot_username}?start=create"
            )
        else:
            await message.answer(
                "برای ساخت قهرمان، لطفاً در گفت‌وگوی خصوصی ربات دستور /start را بزن."
            )
        return

    await state.clear()
    await state.set_state(CharacterCreation.waiting_for_name)

    await message.answer(
        "⚔️ <b>ساخت شخصیت</b>\n\n✍️ نام قهرمانت را وارد کن:",
        parse_mode="HTML",
        reply_to_message_id=message.message_id,
        allow_sending_without_reply=True,
    )
