from __future__ import annotations

import logging
import re
from typing import Any

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.exceptions import TelegramBadRequest
from services.premium_emoji_service import transform_text

logger = logging.getLogger(__name__)
_TAG_RE = re.compile(r"</?tg-emoji\b[^>]*>")


def _effective_parse_mode(method: Any, bot: Any) -> str | None:
    """Resolve aiogram's Default('parse_mode') sentinel against bot defaults."""
    value = getattr(method, "parse_mode", None)
    # aiogram uses a Default sentinel for omitted per-method values. str(value)
    # looks like "Default('parse_mode')"; do not treat that as an explicit mode.
    if value is not None and (
        value.__class__.__name__ == "Default"
        or str(value).lower().startswith("default(")
    ):
        defaults = getattr(bot, "default", None)
        value = getattr(defaults, "parse_mode", None)
    if value is None:
        return None
    return str(getattr(value, "value", value)).upper()


class PremiumEmojiMiddleware(BaseRequestMiddleware):
    """Apply configured custom emojis to HTML text/captions before Bot API calls."""

    async def __call__(self, make_request, bot, method):
        parse_mode = _effective_parse_mode(method, bot)
        is_html = bool(parse_mode and "HTML" in parse_mode and "MARKDOWN" not in parse_mode)
        has_explicit_entities = bool(
            getattr(method, "entities", None) or getattr(method, "caption_entities", None)
        )
        updates: dict[str, str] = {}

        if is_html and not has_explicit_entities:
            for field in ("text", "caption"):
                value = getattr(method, field, None)
                if isinstance(value, str) and value:
                    converted = transform_text(value)
                    if converted != value:
                        updates[field] = converted

        outgoing = method.model_copy(update=updates) if updates else method
        try:
            return await make_request(bot, outgoing)
        except TelegramBadRequest as exc:
            message = str(exc).lower()
            if "entity_text_invalid" not in message and "can't parse entities" not in message:
                raise
            fallback_updates = {}
            for field in ("text", "caption"):
                value = getattr(outgoing, field, None)
                if isinstance(value, str) and "tg-emoji" in value:
                    fallback_updates[field] = _TAG_RE.sub("", value)
            if not fallback_updates:
                raise
            logger.warning("Telegram rejected custom emoji markup; retrying with ordinary emoji glyphs")
            safe_method = outgoing.model_copy(update=fallback_updates)
            return await make_request(bot, safe_method)
