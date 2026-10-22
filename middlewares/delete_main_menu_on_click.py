from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)

_MAIN_MENU_MARKERS = (
    "🎮 <b>منوی اصلی World Eldoria</b>",
    "🎮 <b>منوی اصلی اِلدوریا</b>",
)


class DeleteMainMenuOnClickMiddleware(BaseMiddleware):
    """Delete only the main-menu message before handling its clicked button."""

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        message = event.message
        if message is not None:
            content = message.text or message.caption or ""
            if any(content.startswith(marker) for marker in _MAIN_MENU_MARKERS):
                try:
                    await message.delete()
                except Exception:
                    # A stale/deleted menu must not block the selected action.
                    logger.debug(
                        "Could not delete clicked main-menu message %s in chat %s",
                        message.message_id,
                        message.chat.id,
                        exc_info=True,
                    )

        return await handler(event, data)
