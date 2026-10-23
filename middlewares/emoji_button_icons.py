from __future__ import annotations

import re
from typing import Any

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import TelegramMethod
from aiogram.types import InlineKeyboardMarkup

from services.emoji_manager_service import ALL_BUTTONS, get_emoji


def _normalize_label(text: str) -> str:
    """Normalize a button label so it can be matched even if callback_data differs."""
    value = (text or "").strip()
    # Remove the leading icon/token, leaving the human-readable label.
    if " " in value:
        value = value.split(" ", 1)[1].strip()
    value = re.sub(r"\s+", " ", value)
    return value.casefold()


_LABEL_TO_KEY = {_normalize_label(label): key for key, (label, _emoji) in ALL_BUTTONS.items()}


class EmojiButtonIconsMiddleware(BaseRequestMiddleware):
    """Apply emoji overrides to supported outgoing inline keyboard buttons."""

    async def __call__(self, make_request, bot, method: TelegramMethod[Any]) -> Any:
        markup = getattr(method, "reply_markup", None)
        if not isinstance(markup, InlineKeyboardMarkup):
            return await make_request(bot, method)

        changed = False
        rows = []
        for row in markup.inline_keyboard:
            new_row = []
            for button in row:
                text = button.text or ""
                callback_data = getattr(button, "callback_data", None)
                key = callback_data if callback_data in ALL_BUTTONS else None
                if key is None:
                    key = _LABEL_TO_KEY.get(_normalize_label(text))
                if key is None:
                    new_row.append(button)
                    continue

                # get_emoji returns the saved override or the default for this key.
                emoji = get_emoji(key)
                if not emoji:
                    new_row.append(button)
                    continue

                stripped = text.lstrip()
                first_space = stripped.find(" ")
                if first_space >= 0:
                    new_text = emoji + " " + stripped[first_space + 1:].lstrip()
                else:
                    new_text = emoji + " " + stripped
                if new_text != text:
                    button = button.model_copy(update={"text": new_text})
                    changed = True
                new_row.append(button)
            rows.append(new_row)

        if changed:
            method = method.model_copy(update={
                "reply_markup": markup.model_copy(update={"inline_keyboard": rows})
            })
        return await make_request(bot, method)
