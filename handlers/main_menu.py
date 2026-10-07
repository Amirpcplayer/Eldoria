from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.main_menu import main_menu_keyboard


router = Router()


@router.callback_query(F.data == "menu:back")
async def main_menu_back_handler(
    callback: CallbackQuery,
):
    await callback.message.edit_text(
        "🎮 **منوی اصلی World Eldoria**\n\n"
        "🌌 ماجراجویی تو در اِلدوریا ادامه دارد...",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )

    await callback.answer()