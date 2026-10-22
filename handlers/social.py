from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def social_menu(language: str = "fa"):
    labels = {
        "fa": ("🔙 بازگشت", "🔨 ساخت‌وساز", "🐾 حیوانات", "🎉 رویدادها", "👥 پارتی", "🛡️ گیلد", "🏰 دانجن", "🏆 رتبه‌بندی"),
        "en": ("🔙 Back", "🔨 Crafting", "🐾 Pets", "🎉 Events", "👥 Party", "🛡️ Guild", "🏰 Dungeon", "🏆 Ranking"),
        "ru": ("🔙 Назад", "🔨 Ремесло", "🐾 Питомцы", "🎉 События", "👥 Группа", "🛡️ Гильдия", "🏰 Подземелье", "🏆 Рейтинг"),
    }
    back, crafting, pets, events, party, guild, dungeon, ranking = labels.get(language, labels["fa"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ PvP", callback_data="menu:pvp"), InlineKeyboardButton(text=crafting, callback_data="menu:crafting")],
        [InlineKeyboardButton(text=pets, callback_data="menu:pets"), InlineKeyboardButton(text=events, callback_data="menu:events")],
        [InlineKeyboardButton(text=party, callback_data="menu:party"), InlineKeyboardButton(text=guild, callback_data="menu:guild")],
        [InlineKeyboardButton(text=dungeon, callback_data="menu:dungeon"), InlineKeyboardButton(text=ranking, callback_data="menu:ranking")],
        [InlineKeyboardButton(text=back, callback_data="menu:back")],
    ])
