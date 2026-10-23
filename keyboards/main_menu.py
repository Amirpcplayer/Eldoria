from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 پروفایل",
                    callback_data="menu:profile",
                ),
                InlineKeyboardButton(
                    text="🗃 صندوقچه",
                    callback_data="menu:inventory",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚔️ مهارت‌ها",
                    callback_data="menu:skills",
                ),
                InlineKeyboardButton(
                    text="🛡️ تجهیزات",
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
                    text="🔨 کرفتینگ",
                    callback_data="menu:crafting",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🐾 پت",
                    callback_data="menu:pets",
                ),
                InlineKeyboardButton(
                    text="🎉 ایونت",
                    callback_data="menu:events",
                ),
            ],
            [
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
                InlineKeyboardButton(text="⚒️ آهنگری", callback_data="menu:forge"),
                InlineKeyboardButton(text="🏪 بازار بازیکنان", callback_data="menu:marketplace"),
            ],
            [
                InlineKeyboardButton(text="📖 دفترچهٔ هیولا", callback_data="menu:bestiary"),
            ],
            [
                InlineKeyboardButton(text="💱 تبدیل گلد به جم", callback_data="menu:exchange"),
                InlineKeyboardButton(text="📖 راهنما", callback_data="menu:guide"),
            ],
            [
                InlineKeyboardButton(text="🌟 پیشرفت سریع", callback_data="guide:progress"),
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