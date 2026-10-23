from __future__ import annotations

from typing import Any

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import TelegramMethod
from aiogram.types import InlineKeyboardMarkup

from services.emoji_manager_service import get_emoji


class EmojiButtonIconsMiddleware(BaseRequestMiddleware):
    """Apply per-button ordinary Unicode emoji overrides to outgoing inline keyboards."""

    async def __call__(self, make_request, bot, method: TelegramMethod[Any]) -> Any:
        markup = getattr(method, "reply_markup", None)
        if not isinstance(markup, InlineKeyboardMarkup):
            return await make_request(bot, method)

        changed = False
        rows = []
        for row in markup.inline_keyboard:
            new_row = []
            for button in row:
                callback_data = getattr(button, "callback_data", None)
                if not callback_data:
                    new_row.append(button)
                    continue
                emoji = get_emoji(callback_data)
                if not emoji:
                    new_row.append(button)
                    continue
                # Replace only the leading emoji-like token; preserve all button wording.
                text = button.text or ""
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
