from __future__ import annotations

from urllib.parse import quote
from typing import Any


async def get_bot_deep_link(bot: Any, start_param: str | None = None) -> str | None:
    """Return a Telegram deep link for the currently running bot.

    Never hard-code a bot username: development, staging, and production bots
    may use different usernames. Returns None if Telegram reports no username.
    """
    me = await bot.get_me()
    username = getattr(me, "username", None)
    if not username:
        return None

    url = f"https://t.me/{username}"
    if start_param:
        url += f"?start={quote(start_param, safe='')}"
    return url
