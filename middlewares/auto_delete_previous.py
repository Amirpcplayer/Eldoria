from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import DeleteMessage
from aiogram.types import Message

logger = logging.getLogger(__name__)

# These bot messages are part of gameplay history and must never be cleaned up.
PROTECTED_TERMS = (
    "combat", "battle", "boss", "dungeon", "pvp", "loot", "reward",
    "مبارزه", "نبرد", "کامبت", "باس", "دانجن", "سیاهچال", "حمله",
    "جادو", "ضربه", "آسیب", "غنیمت", "جایزه", "پاداش", "دریافت پاداش",
    "هیل", "شفا داد", "ریکاوری", "معجون",
    "دفتر غنایم", "پیروزی", "شکست خورد", "جایزهٔ حمله", "جایزه شکار",
    "سیاهچال", "سیاه‌چال", "حمله به باس", "ریکاوری کرد", "خود را شفا داد",
)

SEND_METHODS = {
    "SendMessage", "SendPhoto", "SendAudio", "SendDocument", "SendVideo",
    "SendAnimation", "SendVoice", "SendVideoNote", "SendSticker",
    "SendLocation", "SendVenue", "SendContact", "SendPoll", "SendDice",
    "SendMediaGroup",
}


class AutoDeletePreviousMessageMiddleware(BaseRequestMiddleware):
    """Replace the previous ordinary bot reply, but preserve game/combat/reward messages."""

    def __init__(self) -> None:
        self._last_temporary_messages: dict[int, int] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, chat_id: int) -> asyncio.Lock:
        if chat_id not in self._locks:
            self._locks[chat_id] = asyncio.Lock()
        return self._locks[chat_id]

    @staticmethod
    def _message_text(method: Any) -> str:
        return " ".join(str(getattr(method, field, "") or "") for field in ("text", "caption")).casefold()

    @classmethod
    def _is_protected(cls, method: Any) -> bool:
        text = cls._message_text(method)
        return any(term in text for term in PROTECTED_TERMS)

    async def __call__(self, make_request: Any, bot: Any, method: Any) -> Any:
        if method.__class__.__name__ not in SEND_METHODS:
            return await make_request(bot, method)

        chat_id = getattr(method, "chat_id", None)
        if isinstance(chat_id, bool) or not isinstance(chat_id, int):
            return await make_request(bot, method)

        # Keep each protected message independent: it is neither deleted nor tracked.
        if self._is_protected(method):
            return await make_request(bot, method)

        async with self._lock_for(chat_id):
            previous_id = self._last_temporary_messages.get(chat_id)
            if previous_id is not None:
                try:
                    await make_request(bot, DeleteMessage(chat_id=chat_id, message_id=previous_id))
                except Exception:
                    logger.debug(
                        "Previous temporary bot message could not be deleted (chat_id=%s message_id=%s)",
                        chat_id, previous_id, exc_info=True,
                    )
                finally:
                    self._last_temporary_messages.pop(chat_id, None)

            result = await make_request(bot, method)
            if isinstance(result, Message):
                self._last_temporary_messages[chat_id] = result.message_id
            return result
