from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from services.combat_service import get_active_battle_for_player


COMBAT_CALLBACK_PREFIXES = ("combat:", "adventure:fight:")
NOTICE = "⚔️ تا وقتی مبارزهٔ ماجراجویی تمام نشده، نمی‌توانی وارد بخش دیگری شوی. ابتدا مبارزه را تمام کن."


class AdventureFightLockMiddleware(BaseMiddleware):
    """Prevents private-chat navigation while the user has an active adventure battle."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        if event.message is None or event.message.chat.type != "private":
            return await handler(event, data)

        callback_data = event.data or ""
        if callback_data.startswith(COMBAT_CALLBACK_PREFIXES):
            return await handler(event, data)

        telegram_id = event.from_user.id
        try:
            battle = await get_active_battle_for_player(telegram_id)
            if battle is not None:
                await event.answer(NOTICE, show_alert=True)
                return None
        except Exception:
            # Fail open if Redis is temporarily unavailable; do not lock the bot UI.
            import logging
            logging.getLogger(__name__).exception(
                "Could not check active adventure battle for navigation lock"
            )

        return await handler(event, data)
