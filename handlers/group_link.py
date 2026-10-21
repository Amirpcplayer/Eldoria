from __future__ import annotations

import html
import logging
from urllib.parse import quote

from aiogram import F, Router
from aiogram.types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from bot.bot import bot

router = Router(name="group_link")
logger = logging.getLogger(__name__)


@router.message(
    F.chat.type.in_({"group", "supergroup"}),
    F.text.func(
        lambda text: bool(text)
        and text.strip().casefold() in {"لینک", "لینک گروه", "لینکگروه"}
    ),
)
async def group_invite_link(message: Message) -> None:
    try:
        invite = await bot.export_chat_invite_link(message.chat.id)
    except Exception:
        logger.exception(
            "Could not create invite link for chat_id=%s", message.chat.id
        )
        await message.reply(
            "🔒 برای ساخت لینک دعوت، ربات باید در این گروه اجازهٔ افزودن "
            "کاربران/مدیریت لینک دعوت داشته باشد."
        )
        return

    group_title = message.chat.title or "گروه"
    safe_group_title = html.escape(group_title)
    share_url = (
        "https://t.me/share/url?url="
        + quote(invite, safe="")
        + "&text="
        + quote(f"به گروه {group_title} دعوت شده‌ای!", safe="")
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 کپی لینک",
                    copy_text=CopyTextButton(text=invite),
                ),
                InlineKeyboardButton(
                    text="📨 اشتراک‌گذاری",
                    url=share_url,
                ),
            ]
        ]
    )

    await message.reply(
        "🔗 <b>لینک دعوت گروه</b>\n\n"
        f"<b>{safe_group_title}</b>\n\n"
        "لینک دعوت آماده است.\n"
        "می‌تونی اون رو کپی کنی یا با دوستانت به اشتراک بذاری.\n\n"
        "━━━━━━━━━━━━━━━━━━",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
