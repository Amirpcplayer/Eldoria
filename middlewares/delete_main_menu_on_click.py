from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)

OWNER_PREFIX = "eo:"
_MAIN_MENU_MARKERS = (
    "🎮 منوی اصلی World Eldoria",
    "🎮 منوی اصلی اِلدوریا",
)


class DeleteMainMenuOnClickMiddleware(BaseMiddleware):
    """Delete a clicked main menu only when its owner clicked its button."""

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        message = event.message
        callback_data = event.data or ""

        # Menu callbacks are protected as eo:<owner_id>:<original_callback>.
        # Never delete another player's menu before PanelOwnerMiddleware rejects
        # their click.
        owner_id: int | None = None
        if callback_data.startswith(OWNER_PREFIX):
            try:
                _, owner_text, _ = callback_data.split(":", 2)
                owner_id = int(owner_text)
            except (ValueError, TypeError):
                owner_id = None

        is_owner_click = owner_id is not None and owner_id == event.from_user.id

        if message is not None and is_owner_click:
            content = message.text or message.caption or ""
            if any(content.lstrip().startswith(marker) for marker in _MAIN_MENU_MARKERS):
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
