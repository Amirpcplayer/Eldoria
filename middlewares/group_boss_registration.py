from __future__ import annotations

import logging
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Any, Awaitable, Callable

from handlers.group_boss import register_group

logger = logging.getLogger(__name__)
_REGISTERED_GROUPS: set[int] = set()

class GroupBossRegistrationMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]], event: Message, data: dict[str, Any]) -> Any:
        try:
            if event.chat and event.chat.type in {"group", "supergroup"} and event.chat.id not in _REGISTERED_GROUPS:
                await register_group(event.chat.id, event.chat.title or "گروه اِلدوریا")
                _REGISTERED_GROUPS.add(event.chat.id)
        except Exception:
            logger.exception("Could not register group for hourly boss; chat_id=%s", getattr(getattr(event, "chat", None), "id", None))
        return await handler(event, data)
