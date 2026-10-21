from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from database.redis import redis


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
            async for key in redis.scan_iter(match="eldoria:battle:*"):
                if isinstance(key, bytes):
                    key = key.decode("utf-8")

                if ":battle_reward:" in key:
                    continue

                battle_data = await redis.hgetall(key)
                if not battle_data:
                    continue

                owner = battle_data.get("telegram_id", 0)
                if isinstance(owner, bytes):
                    owner = owner.decode("utf-8")

                try:
                    if int(owner) != telegram_id:
                        continue
                except (TypeError, ValueError):
                    continue

                battle_id = key.rsplit(":", 1)[-1]
                from services.combat_service import get_battle

                battle = await get_battle(battle_id)
                if battle is None:
                    continue

                try:
                    player_hp = int(battle.get("player_hp", 0))
                    enemy_hp = int(battle.get("enemy_hp", 0))
                except (TypeError, ValueError):
                    continue

                if player_hp > 0 and enemy_hp > 0:
                    await event.answer(NOTICE, show_alert=True)
                    return None
        except Exception:
            # Fail open if Redis is temporarily unavailable; do not lock the bot UI.
            import logging
            logging.getLogger(__name__).exception(
                "Could not check active adventure battle for navigation lock"
            )

        return await handler(event, data)
