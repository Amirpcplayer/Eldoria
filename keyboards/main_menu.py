from services.language_service import tr
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(language: str = "fa") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=tr(language, "profile"),
                    callback_data="menu:profile",
                ),
                InlineKeyboardButton(
                    text=tr(language, "inventory"),
                    callback_data="menu:inventory",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(language, "skills"),
                    callback_data="menu:skills",
                ),
                InlineKeyboardButton(
                    text=tr(language, "equipment"),
                    callback_data="menu:equipment",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(language, "quest"),
                    callback_data="menu:quest",
                ),
                InlineKeyboardButton(
                    text=tr(language, "adventure"),
                    callback_data="menu:adventure",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(language, "crafting"),
                    callback_data="menu:crafting",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(language, "pets"),
                    callback_data="menu:pets",
                ),
                InlineKeyboardButton(
                    text=tr(language, "events"),
                    callback_data="menu:events",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(language, "party"),
                    callback_data="menu:party",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(language, "guild"),
                    callback_data="menu:guild",
                ),
                InlineKeyboardButton(
                    text=tr(language, "ranking"),
                    callback_data="menu:ranking",
                ),
            ],
            [
                InlineKeyboardButton(text=tr(language, "forge"), callback_data="menu:forge"),
                InlineKeyboardButton(text=tr(language, "marketplace"), callback_data="menu:marketplace"),
            ],
            [
                InlineKeyboardButton(text=tr(language, "bestiary"), callback_data="menu:bestiary"),
            ],
            [
                InlineKeyboardButton(text=tr(language, "exchange"), callback_data="menu:exchange"),
                InlineKeyboardButton(text=tr(language, "guide"), callback_data="menu:guide"),
            ],
            [
                InlineKeyboardButton(
                    text=tr(language, "shop"),
                    callback_data="menu:shop",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(language, "settings_button"),
                    callback_data="menu:settings",
                ),
            ],
        ]
    )


def enter_game_keyboard(language: str = "fa") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text={"en": "🎮 Enter Game", "ru": "🎮 Войти в игру"}.get(language, "🎮 ورود به بازی"),
                    callback_data="menu:enter_game",
                )
            ]
        ]
    )