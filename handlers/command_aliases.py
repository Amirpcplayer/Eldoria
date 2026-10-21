from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

router = Router(name="command_aliases")

# Telegram command names must be lowercase ASCII. Each command opens its
# corresponding in-game section through that section's existing callback.
ALIASES = {
    "sandoghche": ("🗃 صندوقچه", "menu:inventory"),
    "skills": ("⚔️ مهارت‌ها", "menu:skills"),
    "tajhizat": ("🛡 تجهیزات", "menu:equipment"),
    "mamoriah": ("📜 مأموریت‌ها", "menu:quest"),
    "mamoriat": ("📜 مأموریت‌ها", "menu:quest"),
    "majarajoyi": ("🗺 ماجراجویی", "menu:adventure"),
    "majarajooei": ("🗺 ماجراجویی", "menu:adventure"),
    "crafting": ("⚒️ کرفتینگ", "menu:crafting"),
    "pet": ("🐾 پت", "menu:pets"),
    "event": ("🎉 ایونت", "menu:events"),
    "parti": ("👥 پارتی", "menu:party"),
    "party": ("👥 پارتی", "menu:party"),
    "guild": ("🛡️ گیلد", "menu:guild"),
    "player_shop": ("🏪 بازار بازیکنان", "menu:marketplace"),
    "ahangari": ("⚒️ آهنگری", "menu:forge"),
    "help": ("📖 راهنما", "menu:guide"),
    "change": ("💱 تبدیل گلد به جم", "menu:exchange"),
    "setting": ("⚙️ تنظیمات", "menu:settings"),
    "settings": ("⚙️ تنظیمات", "menu:settings"),
}

@router.message(Command(*ALIASES.keys(), ignore_case=True))
async def command_alias(message: Message):
    if not message.from_user:
        return
    command = (message.text or "").split(maxsplit=1)[0].split("@", 1)[0].lstrip("/").lower()
    item = ALIASES.get(command)
    if not item:
        return
    title, callback_data = item
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"باز کردن {title}", callback_data=callback_data)
    ]])
    await message.answer(
        f"{title}\n\nبرای ورود به این بخش، دکمهٔ زیر را بزن:",
        reply_markup=keyboard,
    )
