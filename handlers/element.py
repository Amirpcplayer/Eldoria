from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.main_menu import main_menu_keyboard
from services.language_service import get_language


router = Router()


_ELEMENT_TEXT = {
    "fa": {
        "skills_alert": "✨ انتخاب جادو از بخش مهارت‌ها انجام می‌شود.",
        "welcome": "🌌 به اِلدوریا خوش آمدی!\\n\\n🎮 منوی اصلی بازی:",
        "enter": "🎮 ورود به بازی",
    },
    "en": {
        "skills_alert": "✨ Choose spells from the Skills section.",
        "welcome": "🌌 Welcome to Eldoria!\\n\\n🎮 Main game menu:",
        "enter": "🎮 Enter the game",
    },
    "ru": {
        "skills_alert": "✨ Выбирай заклинания в разделе навыков.",
        "welcome": "🌌 Добро пожаловать в Элдорию!\\n\\n🎮 Главное меню игры:",
        "enter": "🎮 Войти в игру",
    },
}


@router.callback_query(lambda callback: callback.data and callback.data.startswith("element:"))
async def removed_element_handler(callback: CallbackQuery, state: FSMContext):
    language = await get_language(callback.from_user.id)
    language = language if language in _ELEMENT_TEXT else "fa"
    await callback.answer(_ELEMENT_TEXT[language]["skills_alert"], show_alert=True)


@router.callback_query(lambda callback: callback.data == "menu:enter_game")
async def enter_game_handler(callback: CallbackQuery):
    language = await get_language(callback.from_user.id)
    language = language if language in _ELEMENT_TEXT else "fa"
    if callback.message is not None:
        await callback.message.answer(
            _ELEMENT_TEXT[language]["welcome"],
            reply_markup=main_menu_keyboard(language),
        )
    await callback.answer()
