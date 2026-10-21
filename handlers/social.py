from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def social_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⚔️ PvP',callback_data='menu:pvp'),InlineKeyboardButton(text='🔨 Crafting',callback_data='menu:crafting')],
        [InlineKeyboardButton(text='🐾 Pets',callback_data='menu:pets'),InlineKeyboardButton(text='🎉 Events',callback_data='menu:events')],
        [InlineKeyboardButton(text='👥 Party',callback_data='menu:party'),InlineKeyboardButton(text='🛡️ Guild',callback_data='menu:guild')],
        [InlineKeyboardButton(text='🏰 Dungeon',callback_data='menu:dungeon'),InlineKeyboardButton(text='🏆 Ranking',callback_data='menu:ranking')],
        [InlineKeyboardButton(text='🔙 بازگشت',callback_data='menu:back')],
    ])
