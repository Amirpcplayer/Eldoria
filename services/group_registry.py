from __future__ import annotations

import logging
from aiogram import Bot
from sqlalchemy import select
from bot.bot import bot as default_bot
from database.database import AsyncSessionLocal
from models.world_systems import GroupBoss

logger = logging.getLogger(__name__)


async def refresh_registered_group_titles(bot: Bot | None = None) -> None:
    """Refresh cached group names from Telegram without changing stable chat IDs."""
    active_bot = bot or default_bot
    async with AsyncSessionLocal() as session:
        groups = list((await session.scalars(select(GroupBoss))).all())
        group_ids = [int(group.chat_id) for group in groups]

    for chat_id in group_ids:
        try:
            live_chat = await active_bot.get_chat(chat_id)
            title = (getattr(live_chat, "title", None) or "گروه اِلدوریا").strip()[:255]
            async with AsyncSessionLocal() as session:
                row = await session.scalar(select(GroupBoss).where(GroupBoss.chat_id == chat_id))
                if row is not None and row.chat_title != title:
                    row.chat_title = title
                    await session.commit()
        except Exception:
            # Keep the last known title if Telegram temporarily cannot be queried.
            logger.debug("Could not refresh title for group %s", chat_id, exc_info=True)
