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
    "fan art", "fanart", "فن ارت", "فن‌آرت", "فن آرت",
    "پرداخت", "رسید", "سفارش", "در حال ثبت سفارش", "منتظر پرداخت", "منتظر رسید",
    "دفتر غنایم", "پیروزی", "شکست خورد", "جایزهٔ حمله", "جایزه شکار",
    "سیاهچال", "سیاه‌چال", "حمله به باس", "ریکاوری کرد", "خود را شفا داد",
    # پنل و تمام پیام‌های مربوط به مدیریت گروه، همیشه از پاک‌سازی خودکار مستثنا هستند.
    "مدیریت گروه", "نگهبان اِلدوریا", "راهنمای نگهبان", "مدیران ثبت‌شده",
    "فهرست مدیران نگهبان", "مدیران نگهبان", "تنظیم خوشامدگویی", "پیش‌نمایش خوشامدگویی",
    "خوشامدگویی ذخیره و فعال شد", "فقط مدیران گروه", "مالک واقعی این گروه", "مالک کل نگهبان",
    # Moderation confirmations are persistent group history, not temporary menus.
    "اخطار ثبت شد", "اخطار سوم", "اخطارهای این عضو", "اخطارها پاک شدند",
    "سکوت کاربر فعال شد", "سکوت کاربر برداشته شد", "رفع بن برای شناسه",
    "رفع مسدودسازی", "کاربر با موفقیت مسدود شد", "عضو اخراج شد",
    "واژهٔ", "واژه‌های فیلترشده", "فیلتر گروه", "عملیات فیلتر لغو شد",
    "قوانین ذخیره شد", "قوانین گروه", "مدت سکوت", "محدودکردن اعضا",
    "روی پیام عضو ریپلای کن", "این عملیات روی مدیران گروه", "دسترسی فقط برای مدیران",
    "این فرمان مخصوص مدیران گروه", "این فرمان مخصوص مدیران", "اخطارها پاک",
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
        # Track temporary panels independently per chat AND panel owner. Without
        # the owner dimension, one player's button press can delete another
        # player's bot message in the same group.
        self._last_temporary_messages: dict[tuple[int, int | None], int] = {}
        self._locks: dict[tuple[int, int | None], asyncio.Lock] = {}

    @staticmethod
    def _panel_owner_id(method: Any) -> int | None:
        markup = getattr(method, "reply_markup", None)
        for row in getattr(markup, "inline_keyboard", None) or []:
            for button in row:
                data = getattr(button, "callback_data", None) or ""
                parts = data.split(":")
                if len(parts) >= 3 and parts[0] == "eo":
                    try:
                        return int(parts[1])
                    except ValueError:
                        continue
        return None

    def _lock_for(self, key: tuple[int, int | None]) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

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

        # Fan Art and other standalone images must remain visible. Never register
        # photo/media-group sends as temporary messages, even when their caption
        # does not contain a protected keyword.
        if method.__class__.__name__ in {"SendPhoto", "SendMediaGroup"}:
            return await make_request(bot, method)

        # Keep each protected message independent: it is neither deleted nor tracked.
        if self._is_protected(method):
            return await make_request(bot, method)

        key = (chat_id, self._panel_owner_id(method))
        async with self._lock_for(key):
            previous_id = self._last_temporary_messages.get(key)
            if previous_id is not None:
                try:
                    await make_request(bot, DeleteMessage(chat_id=chat_id, message_id=previous_id))
                except Exception:
                    logger.debug(
                        "Previous temporary bot message could not be deleted (chat_id=%s message_id=%s)",
                        chat_id, previous_id, exc_info=True,
                    )
                finally:
                    self._last_temporary_messages.pop(key, None)

            result = await make_request(bot, method)
            if isinstance(result, Message):
                self._last_temporary_messages[key] = result.message_id
            return result
