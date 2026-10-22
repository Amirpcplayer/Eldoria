from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from database.database import AsyncSessionLocal
from models.character import Character
from keyboards.main_menu import main_menu_keyboard
from services.language_service import get_language, tr
from aiogram.types import CallbackQuery

# Define the router before importing project services so that even if a
# dependency imports this module indirectly, `router` already exists.
router = Router(name="main_menu")

from services.panel_image_service import send_panel, show_panel


MAIN_MENU_TEXT = (
    "🎮 <b>منوی اصلی World Eldoria</b>\n\n"
    "🌌 ماجراجویی تو در اِلدوریا ادامه دارد..."
)


@router.callback_query(F.data == "menu:back")
async def main_menu_back_handler(callback: CallbackQuery) -> None:
    language = await get_language(callback.from_user.id)
    await show_panel(
        callback=callback,
        panel_name="main_menu",
        text=f"{tr(language, 'main_title')}\\n\\n{tr(language, 'main_sub')}",
        reply_markup=main_menu_keyboard(language),
    )
    await callback.answer()


@router.message(F.text.func(lambda text: bool(text) and text.strip().casefold() == "منو"))
@router.message(Command("menu"))
async def menu_command(message: Message):
    if not message.from_user:
        return
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == message.from_user.id)
        )
    if character is None:
        language = await get_language(message.from_user.id)
        messages = {
            "fa": "هنوز حساب کاربری نداری. برای ساخت حساب، در پی‌وی دستور /start را بزن.",
            "en": "You don't have a character yet. Open the bot in private chat and send /start to create one.",
            "ru": "У вас ещё нет персонажа. Откройте личный чат с ботом и отправьте /start, чтобы создать его.",
        }
        await message.answer(messages.get(language, messages["fa"]))
        return
    language = await get_language(message.from_user.id)
    await send_panel(
        message=message,
        panel_name="main_menu",
        text=f"{tr(language, 'main_title')}\\n\\n{tr(language, 'main_sub')}",
        reply_markup=main_menu_keyboard(language),
    )
