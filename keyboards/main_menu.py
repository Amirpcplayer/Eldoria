from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 پروفایل",
                    callback_data="menu:profile",
                ),
                InlineKeyboardButton(
                    text="🗝️ صندوقچه",
                    callback_data="menu:inventory",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚔️ مهارت‌ها",
                    callback_data="menu:skills",
                ),
                InlineKeyboardButton(
                    text="🗡️ تجهیزات",
                    callback_data="menu:equipment",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📜 مأموریت‌ها",
                    callback_data="menu:quest",
                ),
                InlineKeyboardButton(
                    text="🗺️ ماجراجویی",
                    callback_data="menu:adventure",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏰 دانجن",
                    callback_data="menu:dungeon",
                ),
                InlineKeyboardButton(
                    text="👥 پارتی",
                    callback_data="menu:party",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🛡️ گیلد",
                    callback_data="menu:guild",
                ),
                InlineKeyboardButton(
                    text="🏆 رتبه‌بندی",
                    callback_data="menu:ranking",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🛒 فروشگاه",
                    callback_data="menu:shop",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ تنظیمات",
                    callback_data="menu:settings",
                ),
            ],
        ]
    )


def enter_game_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 ورود به بازی",
                    callback_data="menu:enter_game",
                )
            ]
        ]
    )