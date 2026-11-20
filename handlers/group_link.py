from __future__ import annotations

import logging
from urllib.parse import quote

from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton

from bot.bot import bot
from services.language_service import get_language

router = Router(name="group_link")
logger = logging.getLogger(__name__)

_TEXT = {
    "fa": {
        "error": "🔒 برای ساخت لینک دعوت، ربات باید اجازهٔ مدیریت لینک دعوت را داشته باشد.",
        "share": "به گروه {group} دعوت شده‌ای!",
        "copy": "📋 کپی لینک",
        "share_button": "📨 اشتراک‌گذاری",
        "title": "╭─── ✧ دروازهٔ ورود اِلدوریا ✧ ───╮",
        "body": "پیوند این سرزمین آماده است؛ آن را کپی کن یا با دوستانت به اشتراک بگذار.",
        "group": "گروه اِلدوریا",
    },
    "en": {
        "error": "🔒 The bot needs permission to manage invite links in this group.",
        "share": "You've been invited to {group}!",
        "copy": "📋 Copy link",
        "share_button": "📨 Share",
        "title": "╭─── ✧ Eldoria Gateway ✧ ───╮",
        "body": "The invite link is ready. Copy it or share it with your friends.",
        "group": "Eldoria group",
    },
    "ru": {
        "error": "🔒 Боту нужно разрешение на управление ссылками-приглашениями в этой группе.",
        "share": "Вас пригласили в группу {group}!",
        "copy": "📋 Скопировать ссылку",
        "share_button": "📨 Поделиться",
        "title": "╭─── ✧ Врата Элдории ✧ ───╮",
        "body": "Ссылка-приглашение готова. Скопируйте её или поделитесь с друзьями.",
        "group": "группа Элдории",
    },
}


@router.message(
    F.chat.type.in_({"group", "supergroup"}),
    F.text.func(lambda text: bool(text) and text.strip().casefold() in {"لینک", "لینک گروه", "لینکگروه", "link", "group link", "ссылка", "ссылка группы"}),
)
async def group_invite_link(message: Message) -> None:
    language = await get_language(message.from_user.id) if message.from_user else "fa"
    t = _TEXT.get(language, _TEXT["fa"])
    try:
        invite = await bot.export_chat_invite_link(message.chat.id)
    except Exception:
        logger.exception("Could not create invite link for chat_id=%s", message.chat.id)
        await message.reply(t["error"])
        return

    group_name = message.chat.title or t["group"]
    share_url = "https://t.me/share/url?url=" + quote(invite, safe="") + "&text=" + quote(t["share"].format(group=group_name), safe="")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t["copy"], copy_text=CopyTextButton(text=invite)),
        InlineKeyboardButton(text=t["share_button"], url=share_url),
    ]])
    await message.reply(
        f"{t['title']}\n🏰 <b>{group_name}</b>\n\n{t['body']}\n╰────────────────────────╯",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
