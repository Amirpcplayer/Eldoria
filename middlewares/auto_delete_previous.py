from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import DeleteMessage
from aiogram.types import InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)


class AutoDeletePreviousMessageMiddleware(BaseRequestMiddleware):
    """Only clean up stale main-menu panels in private chats.

    Game replies (heal, combat, boss, dungeon, loot, etc.) are never tracked
    or deleted. Group messages are always persistent. A main menu is detected
    by its own menu callbacks, not by message text, so unrelated replies cannot
    accidentally trigger cleanup.
    """

    def __init__(self) -> None:
        self._main_menu_messages: dict[int, int] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, chat_id: int) -> asyncio.Lock:
        lock = self._locks.get(chat_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[chat_id] = lock
        return lock

    @staticmethod
    def _menu_callback_data(method: Any) -> set[str]:
        markup = getattr(method, "reply_markup", None)
        if not isinstance(markup, InlineKeyboardMarkup):
            return set()

        return {
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
            if button.callback_data
        }

    @classmethod
    def _is_main_menu(cls, method: Any) -> bool:
        callbacks = cls._menu_callback_data(method)
        # These are distinctive callbacks from keyboards/main_menu.py.
        return {
            "menu:profile",
            "menu:inventory",
            "menu:skills",
        }.issubset(callbacks)

    @classmethod
    def _is_menu_navigation(cls, method: Any) -> bool:
        # A submenu that links back to the menu can replace the old main menu.
        return any(
            callback.startswith("menu:")
            for callback in cls._menu_callback_data(method)
        )

    async def __call__(self, make_request: Any, bot: Any, method: Any) -> Any:
        method_name = method.__class__.__name__
        if method_name not in {
            "SendMessage",
            "SendPhoto",
            "SendAudio",
            "SendDocument",
            "SendVideo",
            "SendAnimation",
            "SendVoice",
            "SendVideoNote",
            "SendSticker",
            "SendLocation",
            "SendVenue",
            "SendContact",
            "SendPoll",
            "SendDice",
            "SendMediaGroup",
        }:
            return await make_request(bot, method)

        raw_chat_id = getattr(method, "chat_id", None)
        if (
            isinstance(raw_chat_id, bool)
            or not isinstance(raw_chat_id, int)
            or raw_chat_id <= 0
        ):
            # Never auto-delete anything in groups/supergroups/channels.
            return await make_request(bot, method)

        is_main_menu = self._is_main_menu(method)
        is_menu_navigation = self._is_menu_navigation(method)

        # Non-menu messages are always sent as-is and never affect the menu
        # cleanup state. This includes all heal/combat/game replies.
        if not is_main_menu and not is_menu_navigation:
            return await make_request(bot, method)

        async with self._lock_for(raw_chat_id):
            previous_id = self._main_menu_messages.get(raw_chat_id)

            # Only a menu-related UI panel can replace the old main menu.
            if previous_id is not None:
                try:
                    await make_request(
                        bot,
                        DeleteMessage(chat_id=raw_chat_id, message_id=previous_id),
                    )
                except Exception:
                    logger.debug(
                        "Previous main menu could not be deleted "
                        "(chat_id=%s message_id=%s)",
                        raw_chat_id,
                        previous_id,
                        exc_info=True,
                    )
                finally:
                    self._main_menu_messages.pop(raw_chat_id, None)

            result = await make_request(bot, method)

            if is_main_menu and isinstance(result, Message):
                self._main_menu_messages[raw_chat_id] = result.message_id

            return result
