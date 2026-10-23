from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.premium_emoji_service import emoji


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{emoji('menu_profile')} پروفایل", callback_data="menu:profile"),
             InlineKeyboardButton(text=f"{emoji('menu_inventory')} صندوقچه", callback_data="menu:inventory")],
            [InlineKeyboardButton(text=f"{emoji('menu_skills')} مهارت‌ها", callback_data="menu:skills"),
             InlineKeyboardButton(text=f"{emoji('menu_equipment')} تجهیزات", callback_data="menu:equipment")],
            [InlineKeyboardButton(text=f"{emoji('menu_quest')} ماموریت‌ها", callback_data="menu:quest"),
             InlineKeyboardButton(text=f"{emoji('menu_adventure')} ماجراجویی", callback_data="menu:adventure")],
            [InlineKeyboardButton(text=f"{emoji('menu_crafting')} کرفتینگ", callback_data="menu:crafting")],
            [InlineKeyboardButton(text=f"{emoji('menu_pets')} پت", callback_data="menu:pets"),
             InlineKeyboardButton(text=f"{emoji('menu_events')} ایونت", callback_data="menu:events")],
            [InlineKeyboardButton(text=f"{emoji('menu_party')} پارتی", callback_data="menu:party")],
            [InlineKeyboardButton(text=f"{emoji('menu_guild')} گیلد", callback_data="menu:guild"),
             InlineKeyboardButton(text=f"{emoji('menu_ranking')} رتبه‌بندی", callback_data="menu:ranking")],
            [InlineKeyboardButton(text=f"{emoji('menu_forge')} آهنگری", callback_data="menu:forge"),
             InlineKeyboardButton(text=f"{emoji('menu_marketplace')} بازار بازیکنان", callback_data="menu:marketplace")],
            [InlineKeyboardButton(text=f"{emoji('menu_bestiary')} دفترچه هیولا", callback_data="menu:bestiary")],
            [InlineKeyboardButton(text=f"{emoji('menu_exchange')} تبدیل گلد به جم", callback_data="menu:exchange"),
             InlineKeyboardButton(text=f"{emoji('menu_guide')} راهنما", callback_data="menu:guide")],
            [InlineKeyboardButton(text=f"{emoji('menu_shop')} فروشگاه", callback_data="menu:shop")],
            [InlineKeyboardButton(text=f"{emoji('menu_settings')} تنظیمات", callback_data="menu:settings")],
        ]
    )


def enter_game_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{emoji('menu_enter_game')} ورود به بازی", callback_data="menu:enter_game")]
    ])
