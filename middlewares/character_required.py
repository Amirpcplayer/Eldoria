from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character

NOTICE = (
    "༺ ✦ دروازه‌های اِلدوریا ✦ ༻\n\n"
    "برای استفاده از امکانات بازی، ابتدا باید شخصیت خود را بسازی.\n"
    "⚔️ برای آغاز، دکمهٔ زیر را بزن."
)
ALLOWED_COMMANDS = {"start", "cancel", "admin", "myid", "profile", "sandoghche", "skills", "tajhizat", "mamoriah", "mamoriat", "majarajoyi", "majarajooei", "crafting", "pet", "event", "parti", "party", "guild", "player_shop", "ahangari", "help", "change", "setting", "settings", "shop", "menu", "guide", "arts", "mypet", "pvp", "bounty", "attack", "magic", "heal", "mana", "art", "boss_status", "dungeon", "market_items", "market_sell", "market_equipment", "market_sell_equipment", "market_equipment_items", "fanart_add", "remove_boss"}
CREATE_CALLBACK_PREFIXES = ("gender:", "race:")
CREATE_CALLBACKS = {"race:confirm", "race:back"}


class CharacterRequiredMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        if isinstance(event, Message):
            content = (event.text or event.caption or "").strip()
            if content.startswith("/"):
                command = content.split()[0].split("@")[0][1:].lower()
                if command in ALLOWED_COMMANDS:
                    return await handler(event, data)
            elif event.chat.type != "private":
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            cb = event.data or ""
            if cb in CREATE_CALLBACKS or cb.startswith(CREATE_CALLBACK_PREFIXES):
                return await handler(event, data)
        else:
            return await handler(event, data)

        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == user.id)
            )
        if character is not None and character.race and character.name:
            return await handler(event, data)

        state = data.get("state")
        if isinstance(event, Message) and state is not None and await state.get_state():
            return await handler(event, data)

        bot_user = await event.bot.get_me()
        link = f"https://t.me/{bot_user.username}?start=create" if bot_user.username else None
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="⚔️ ساخت شخصیت",
                **({"url": link} if link else {"callback_data": "registration:required"})
            )
        ]])
        if isinstance(event, CallbackQuery):
            await event.answer("ابتدا باید شخصیت بسازی.", show_alert=True)
            if event.message:
                await event.message.answer(NOTICE, reply_markup=keyboard)
        else:
            await event.answer(NOTICE, reply_markup=keyboard)
        return None
