from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import DeleteMessage
from aiogram.types import Message

logger = logging.getLogger(__name__)

# Only ordinary private-chat replies/panels are managed here. Group gameplay
# messages (bosses, combat, dungeon events, etc.) are intentionally untouched.
MESSAGE_METHODS = {
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
}


class AutoDeletePreviousMessageMiddleware(BaseRequestMiddleware):
    """Keep only the latest bot message in each private chat.

    This works at the Bot API request layer, so it covers handlers throughout
    the bot without requiring each router to use a separate helper.
    """

    def __init__(self) -> None:
        self._last_messages: dict[int, list[int]] = defaultdict(list)
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, chat_id: int) -> asyncio.Lock:
        lock = self._locks.get(chat_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[chat_id] = lock
        return lock

    async def __call__(self, make_request: Any, bot: Any, method: Any) -> Any:
        method_name = method.__class__.__name__
        if method_name not in MESSAGE_METHODS:
            return await make_request(bot, method)

        raw_chat_id = getattr(method, "chat_id", None)
        # Telegram user IDs are positive; group/supergroup/channel IDs are
        # negative. Avoid applying private-chat cleanup to group gameplay.
        if isinstance(raw_chat_id, bool) or not isinstance(raw_chat_id, int) or raw_chat_id <= 0:
            return await make_request(bot, method)

        chat_id = raw_chat_id
        async with self._lock_for(chat_id):
            previous_ids = self._last_messages.pop(chat_id, [])
            for message_id in previous_ids:
                try:
                    # Call the request continuation directly to avoid recursively
                    # entering this middleware for the DeleteMessage request.
                    await make_request(
                        bot,
                        DeleteMessage(chat_id=chat_id, message_id=message_id),
                    )
                except Exception:
                    # A previous message may already have been deleted or be
                    # too old to delete. Never block the new reply because of it.
                    logger.debug(
                        "Could not delete previous bot message chat_id=%s message_id=%s",
                        chat_id,
                        message_id,
                        exc_info=True,
                    )

            result = await make_request(bot, method)
            if isinstance(result, Message):
                self._last_messages[chat_id] = [result.message_id]
            elif isinstance(result, list):
                ids = [
                    item.message_id
                    for item in result
                    if isinstance(item, Message)
                ]
                if ids:
                    self._last_messages[chat_id] = ids
            return result
