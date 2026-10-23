from __future__ import annotations

import re
from typing import Any

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import TelegramMethod
from aiogram.types import InlineKeyboardMarkup

from services.emoji_manager_service import ALL_BUTTONS, get_custom_emoji_id, get_emoji


def _normalize_label(text: str) -> str:
    return re.sub(r"\\s+", " ", (text or "").strip()).casefold()


_LABEL_ONLY_TO_KEY: dict[str, str] = {}
_LABEL_TO_KEY: dict[str, str] = {}
for _key, (_label, _default_emoji) in ALL_BUTTONS.items():
    _label_only = _normalize_label(_label)
    _LABEL_ONLY_TO_KEY[_label_only] = _key
    _LABEL_TO_KEY[_label_only] = _key
    _LABEL_TO_KEY[_normalize_label(f"{_default_emoji} {_label}")] = _key


class EmojiButtonIconsMiddleware(BaseRequestMiddleware):
    """Apply standard or Telegram custom-emoji icons to outgoing inline keyboard buttons."""

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
                normalized = _normalize_label(text)
                exact_label_match = normalized in _LABEL_ONLY_TO_KEY

                if key is None:
                    key = _LABEL_TO_KEY.get(normalized)
                    if key is None and " " in normalized:
                        key = _LABEL_TO_KEY.get(normalized.split(" ", 1)[1])

                if key is None:
                    new_row.append(button)
                    continue

                custom_emoji_id = get_custom_emoji_id(key)
                emoji = get_emoji(key)
                if not emoji:
                    new_row.append(button)
                    continue

                stripped = text.lstrip()
                if exact_label_match:
                    label = stripped
                else:
                    first_space = stripped.find(" ")
                    label = stripped[first_space + 1:].lstrip() if first_space >= 0 else stripped

                if custom_emoji_id:
                    # Bot API supports icon_custom_emoji_id on inline keyboard buttons.
                    # model_copy(update=...) keeps compatibility with aiogram versions
                    # whose local model schema has not yet added this Bot API field.
                    button = button.model_copy(update={
                        "text": label,
                        "icon_custom_emoji_id": custom_emoji_id,
                    })
                    changed = True
                else:
                    new_text = emoji + " " + label
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
