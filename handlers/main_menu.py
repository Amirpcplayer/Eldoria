from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from keyboards.main_menu import main_menu_keyboard
from services.panel_image_service import send_panel, show_panel

router = Router(name="main_menu")

MAIN_MENU_TEXT = "🎮 <b>منوی اصلی World Eldoria</b>\\n\\n🌌 ماجراجویی تو در اِلدوریا ادامه دارد..."


@router.callback_query(F.data == "menu:back")
async def main_menu_back_handler(callback: CallbackQuery) -> None:
    await show_panel(
        callback=callback,
        panel_name="main_menu",
        text=MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(),
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
        await message.answer("هنوز حساب کاربری نداری. برای ساخت قهرمان، در پی‌وی دستور /start را بزن.")
        return
    await send_panel(
        message=message,
        panel_name="main_menu",
        text=MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(),
    )
