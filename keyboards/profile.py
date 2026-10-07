from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def profile_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗝️ صندوقچه",
                    callback_data="menu:inventory",
                ),
                InlineKeyboardButton(
                    text="🗡️ تجهیزات",
                    callback_data="menu:equipment",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚔️ مهارت‌ها",
                    callback_data="menu:skills",
                ),
                InlineKeyboardButton(
                    text="📊 آمار کامل",
                    callback_data="profile:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="menu:back",
                ),
            ],
        ]
    )