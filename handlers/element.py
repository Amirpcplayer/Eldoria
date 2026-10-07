from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.main_menu import main_menu_keyboard


router = Router()


@router.callback_query(
    lambda callback: callback.data.startswith("element:")
)
async def removed_element_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer(
        "✨ انتخاب جادو از بخش مهارت‌ها انجام می‌شود.",
        show_alert=True,
    )


@router.callback_query(
    lambda callback: callback.data == "menu:enter_game"
)
async def enter_game_handler(
    callback: CallbackQuery,
):
    await callback.message.edit_text(
        "🌌 به اِلدوریا خوش آمدی!\n\n"
        "🎮 منوی اصلی بازی:",
        reply_markup=main_menu_keyboard(),
    )

    await callback.answer()