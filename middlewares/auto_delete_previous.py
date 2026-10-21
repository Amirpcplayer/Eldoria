from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import DeleteMessage
from aiogram.types import Message

logger = logging.getLogger(__name__)

# Track messages sent by the bot in both private chats and groups. Only IDs
# returned by Telegram for this bot's own messages are stored; player messages
# are never tracked or deleted.
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
    """Keep only the latest bot message(s) in each chat, including groups.

    This works at the Bot API request layer. It only deletes message IDs
    returned from the bot's own send requests, never messages written by users.
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
        # Private chat IDs are positive; group/supergroup/channel IDs are
        # negative. Accept both so cleanup also works in group chats.
        if isinstance(raw_chat_id, bool) or not isinstance(raw_chat_id, int) or raw_chat_id == 0:
            return await make_request(bot, method)

        chat_id = raw_chat_id

        # Group chat messages are persistent game content. Never auto-delete
        # group messages: boss posts, combat logs, dungeon notices and replies
        # must remain available to every player.
        if chat_id < 0:
            return await make_request(bot, method)

        # Keep private-chat combat/boss/dungeon messages too. Do this before
        # cleaning the previous UI panel, so a combat message cannot trigger
        # deletion of earlier game content.
        message_text = str(getattr(method, "text", "") or "")
        message_caption = str(getattr(method, "caption", "") or "")
        content = f"{message_text}\n{message_caption}".casefold()
        protected_terms = (
            "combat", "battle", "boss", "dungeon", "fight",
            "مبارزه", "نبرد", "کامبت", "باس", "دانجن", "سیاهچال",
            "حمله", "جادو", "ضربه", "آسیب", "غنیمت", "شکست خورد",
            "مبارزهٔ ماجراجویی", "ماجراجویی",
        )
        if any(term in content for term in protected_terms):
            result = await make_request(bot, method)
            # Never add this game message to the auto-delete queue.
            if isinstance(result, Message):
                tracked = self._last_messages.get(chat_id, [])
                if result.message_id in tracked:
                    tracked.remove(result.message_id)
            return result

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
                    logger.warning(
                        "Could not delete previous bot message chat_id=%s message_id=%s; "
                        "Telegram API error follows",
                        chat_id,
                        message_id,
                        exc_info=True,
                    )

            result = await make_request(bot, method)
            if isinstance(result, Message):
                logger.info(
                    "Tracked bot message chat_id=%s message_id=%s method=%s",
                    chat_id,
                    result.message_id,
                    method_name,
                )
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
