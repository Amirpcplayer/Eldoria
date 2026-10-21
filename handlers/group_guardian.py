"""Eldoria Guardian: per-group moderation, independent of RPG character creation."""
from __future__ import annotations

import html
import re
import time
from collections import defaultdict, deque

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Message, TelegramObject
from aiogram.exceptions import TelegramAPIError
from datetime import datetime, timedelta, timezone
from database.redis import redis

router = Router()
FLAGS = {"links": "🔗 ضد لینک", "spam": "🌊 ضد فلود", "bots": "🤖 ضد ربات", "words": "🚫 فیلتر کلمات", "welcome": "👋 خوشامدگویی"}
DEFAULTS = {"links": False, "spam": False, "bots": False, "words": False, "welcome": False}
WINDOW = defaultdict(deque)
URL = re.compile(r"(?:https?://|www\.|t\.me/|telegram\.me/|(?:[\w-]+\.)+(?:com|net|org|ir|io|gg|me)(?:/|\b))", re.I)
PERMISSIONS = ChatPermissions(can_send_messages=False)
UNMUTE = ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True, can_invite_users=True)

def group(chat):
    return chat.type in ("group", "supergroup")

async def authorized(bot, chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ("creator", "administrator")

async def bot_rights(bot, chat_id, action):
    me = await bot.get_me()
    member = await bot.get_chat_member(chat_id, me.id)
    if member.status != "administrator":
        return False
    return bool(getattr(member, action, False))


async def guardian_admin(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramAPIError:
        return False
    if member.status == "creator":
        return True
    return str(user_id) in await redis.smembers(f"guardian:{chat_id}:admins")

async def owner_only(bot, chat_id, user_id):
    try:
        return (await bot.get_chat_member(chat_id, user_id)).status == "creator"
    except TelegramAPIError:
        return False

async def settings(chat_id):
    values = await redis.hgetall(f"guardian:{chat_id}:settings")
    return {k: values.get(k, "1" if v else "0") == "1" for k, v in DEFAULTS.items()}

def keyboard(chat_id, values, owner_id):
    rows = [[InlineKeyboardButton(text=f"{label}: {'✅' if values[key] else '❌'}", callback_data=f"gap:toggle:{chat_id}:{owner_id}:{key}")] for key, label in FLAGS.items()]
    rows += [[InlineKeyboardButton(text="🎨 تنظیم متن خوشامدگویی", callback_data=f"gap:welcome:{chat_id}:{owner_id}")], [InlineKeyboardButton(text="👑 مدیران ثبت‌شده", callback_data=f"gap:admins:{chat_id}:{owner_id}")], [InlineKeyboardButton(text="📋 وضعیت و راهنما", callback_data=f"gap:help:{chat_id}:{owner_id}")], [InlineKeyboardButton(text="✖️ بستن", callback_data=f"gap:close:{chat_id}:{owner_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def panel(values):
    return ("🛡️ <b>نگهبان اِلدوریا | مدیریت گروه</b>\n━━━━━━━━━━━━━━━━━━\n"
            "تنظیمات امنیتی این گروه مستقل از سایر گروه‌هاست.\n"
            "برای تغییر هر قابلیت، دکمهٔ آن را انتخاب کنید.\n\n"
            "⚔️ پیام‌های فرمان بازی از فیلتر لینک و فلود مستثنا هستند.\n"
            "🔐 فقط مدیران همین گروه به پنل دسترسی دارند.")

@router.message(Command("gap"))
async def gap(message: Message):
    if not group(message.chat):
        await message.answer("🛡️ دستور /gap را در گروه اجرا کنید.")
        return
    if not await guardian_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ فقط مدیران گروه به این پنل دسترسی دارند.")
        return
    values = await settings(message.chat.id)
    await message.answer(panel(values), reply_markup=keyboard(message.chat.id, values, message.from_user.id))

@router.callback_query(F.data.startswith("gap:"))
async def callback(callback: CallbackQuery):
    if not callback.message or not group(callback.message.chat):
        await callback.answer("پنل فقط در گروه معتبر است.", show_alert=True)
        return
    parts = (callback.data or "").split(":")
    if len(parts) < 4 or not parts[2].lstrip("-").isdigit() or int(parts[2]) != callback.message.chat.id or not parts[3].isdigit():
        await callback.answer("پنل متعلق به این گروه نیست.", show_alert=True)
        return
    if int(parts[3]) != callback.from_user.id:
        await callback.answer("🔒 این پنل برای مدیر دیگری است؛ پنل خودتان را با /gap باز کنید.", show_alert=True)
        return
    if not await guardian_admin(callback.bot, callback.message.chat.id, callback.from_user.id):
        await callback.answer("فقط مدیران ثبت‌شده همین گروه.", show_alert=True)
        return
    action, chat_id, owner_id = parts[1], callback.message.chat.id, callback.from_user.id
    if action == "close":
        await callback.message.edit_reply_markup(reply_markup=None)
    elif action == "help":
        await callback.message.edit_text(
            "🛡️ <b>راهنمای نگهبان</b>\n"
            "روی پیام عضو ریپلای کنید:\n"
            "/warn — اخطار (۳ اخطار = سکوت ۱ ساعته)\n"
            "/mute 60 — سکوت به دقیقه\n"
            "/unmute — رفع سکوت\n"
            "/ban — مسدودسازی\n"
            "/unban USER_ID — رفع مسدودسازی با شناسه عددی\n"
            "/kick — اخراج\n"
            "/warnings — تعداد اخطارها\n"
            "/clearwarn — پاک‌کردن اخطارها\n"
            "/filteradd واژه — افزودن واژه ممنوع\n"
            "/filterdel واژه — حذف واژه\n"
            "/filters — فهرست واژه‌ها\n"
            "/rules متن قوانین — ثبت قوانین\n"
            "/rules — نمایش قوانین\n"
            "/gap — بازگشت به پنل\n\n"
            "برای حذف پیام و محدودکردن اعضا، دسترسی حذف پیام و مسدودسازی به ربات بدهید.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 پنل", callback_data=f"gap:home:{chat_id}:{owner_id}")]]))
    elif action == "home":
        values = await settings(chat_id)
        await callback.message.edit_text(panel(values), reply_markup=keyboard(chat_id, values, owner_id))
    elif action == "toggle" and len(parts) == 5 and parts[4] in FLAGS:
        key = parts[4]
        values = await settings(chat_id)
        values[key] = not values[key]
        await redis.hset(f"guardian:{chat_id}:settings", key, "1" if values[key] else "0")
        await callback.message.edit_text(panel(values), reply_markup=keyboard(chat_id, values))
    await callback.answer()

@router.message(Command("warn", "mute", "unmute", "ban", "unban", "kick", "warnings", "clearwarn", "filteradd", "filterdel", "filters", "rules"))
async def manage(message: Message):
    if not group(message.chat) or not message.from_user:
        return
    command = message.text.split()[0].split("@")[0][1:].lower()
    arg = message.text.partition(" ")[2].strip()
    chat_id = message.chat.id
    if command == "rules" and not arg:
        rules = await redis.get(f"guardian:{chat_id}:rules")
        await message.answer("📜 <b>قوانین گروه</b>\n" + html.escape(rules or "هنوز قانونی ثبت نشده است."))
        return
    if not await guardian_admin(message.bot, chat_id, message.from_user.id):
        await message.answer("⛔ این فرمان مخصوص مدیران گروه است.")
        return
    if command == "rules":
        await redis.set(f"guardian:{chat_id}:rules", arg[:3000])
        await message.answer("✅ قوانین ذخیره شد.")
        return
    if command == "filters":
        words = sorted(await redis.smembers(f"guardian:{chat_id}:words"))
        await message.answer("🚫 واژه‌های فیلترشده:\n" + (html.escape("، ".join(words)) if words else "موردی ثبت نشده است."))
        return
    if command in ("filteradd", "filterdel"):
        if not arg or len(arg) > 60:
            await message.answer("یک واژه یا عبارت حداکثر ۶۰ کاراکتری وارد کنید.")
            return
        key = f"guardian:{chat_id}:words"
        if command == "filteradd":
            await redis.sadd(key, arg.casefold())
        else:
            await redis.srem(key, arg.casefold())
        await message.answer("✅ فیلتر به‌روزرسانی شد.")
        return
    if command == "unban":
        if not arg.lstrip("-").isdigit():
            await message.answer("نمونه: /unban 123456789")
            return
        if not await bot_rights(message.bot, chat_id, "can_restrict_members"):
            await message.answer("ربات مجوز مسدودسازی ندارد.")
            return
        try:
            await message.bot.unban_chat_member(chat_id, int(arg), only_if_banned=True)
            await message.answer("✅ رفع مسدودسازی انجام شد.")
        except TelegramAPIError as exc:
            await message.answer("❌ عملیات ناموفق بود: " + html.escape(str(exc)))
        return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target:
        await message.answer("روی پیام عضو موردنظر ریپلای کنید.")
        return
    if target.is_bot or target.id == message.from_user.id or await authorized(message.bot, chat_id, target.id):
        await message.answer("⛔ این عملیات روی ربات‌ها، خودتان یا مدیران مجاز نیست.")
        return
    key = f"guardian:{chat_id}:warn:{target.id}"
    if command == "warnings":
        await message.answer(f"⚠️ اخطارهای این عضو: {int(await redis.get(key) or 0)}/3")
        return
    if command == "clearwarn":
        await redis.delete(key)
        await message.answer("✅ اخطارها پاک شدند.")
        return
    if not await bot_rights(message.bot, chat_id, "can_restrict_members"):
        await message.answer("❌ ابتدا مجوز محدودکردن اعضا را به ربات بدهید.")
        return
    try:
        if command == "warn":
            count = await redis.incr(key)
            if count >= 3:
                await message.bot.restrict_chat_member(chat_id, target.id, permissions=PERMISSIONS, until_date=datetime.now(timezone.utc) + timedelta(hours=1))
                await redis.delete(key)
                await message.answer("⚠️ اخطار سوم؛ عضو برای یک ساعت ساکت شد.")
            else:
                await message.answer(f"⚠️ اخطار ثبت شد: {count}/3")
        elif command == "mute":
            minutes = int(arg) if arg.isdigit() else 60
            if not 1 <= minutes <= 525600:
                await message.answer("مدت سکوت باید بین ۱ تا ۵۲۵۶۰۰ دقیقه باشد.")
                return
            await message.bot.restrict_chat_member(chat_id, target.id, permissions=PERMISSIONS, until_date=datetime.now(timezone.utc) + timedelta(minutes=minutes))
            await message.answer(f"🔇 عضو برای {minutes} دقیقه ساکت شد.")
        elif command == "unmute":
            await message.bot.restrict_chat_member(chat_id, target.id, permissions=UNMUTE)
            await message.answer("🔊 سکوت عضو برداشته شد.")
        elif command == "ban":
            await message.bot.ban_chat_member(chat_id, target.id)
            await message.answer("⛔ عضو مسدود شد.")
        elif command == "kick":
            await message.bot.ban_chat_member(chat_id, target.id)
            await message.bot.unban_chat_member(chat_id, target.id, only_if_banned=True)
            await message.answer("🚪 عضو اخراج شد.")
    except (TelegramAPIError, ValueError) as exc:
        await message.answer("❌ عملیات ناموفق بود: " + html.escape(str(exc)))


@router.message(Command("add_admin", "remove_admin", "admins", "update"))
async def admin_roster(message: Message):
    if not group(message.chat) or not message.from_user:
        await message.answer("این دستور را داخل گروه اجرا کن.")
        return
    chat_id, uid = message.chat.id, message.from_user.id
    cmd = message.text.split()[0].split("@")[0][1:].lower()
    arg = message.text.partition(" ")[2].strip()
    if cmd == "admins":
        ids = sorted(await redis.smembers(f"guardian:{chat_id}:admins"))
        lines = ["👑 <b>فهرست مدیران نگهبان</b>", "♛ شاه: مالک واقعی گروه"]
        for item in ids:
            try:
                m = await message.bot.get_chat_member(chat_id, int(item))
                lines.append(f"🛡️ {html.escape(m.user.full_name)} — <code>{item}</code>")
            except TelegramAPIError:
                lines.append(f"🛡️ <code>{item}</code>")
        await message.answer("\\n".join(lines))
        return
    if cmd == "update":
        if not await owner_only(message.bot, chat_id, uid):
            await message.answer("⛔ فقط مالک واقعی گروه می‌تواند /update را اجرا کند.")
            return
        actual = {str(m.user.id) for m in await message.bot.get_chat_administrators(chat_id) if not m.user.is_bot}
        key = f"guardian:{chat_id}:admins"
        await redis.delete(key)
        if actual: await redis.sadd(key, *actual)
        await message.answer("🔄 فهرست مدیران همگام‌سازی شد؛ فقط مدیران واقعی گروه باقی ماندند.")
        return
    if not await owner_only(message.bot, chat_id, uid):
        await message.answer("⛔ فقط مالک واقعی گروه می‌تواند مدیر تعیین یا عزل کند.")
        return
    target_id = None
    if message.reply_to_message and message.reply_to_message.from_user and not arg:
        target_id = message.reply_to_message.from_user.id
    elif arg.lstrip("-").isdigit():
        target_id = int(arg)
    if not target_id:
        await message.answer("شناسه عددی کاربر را بده یا روی پیام او ریپلای کن: /add_admin 123456789")
        return
    if target_id == uid:
        await message.answer("مالک گروه از قبل لقب شاه را دارد.")
        return
    try: member = await message.bot.get_chat_member(chat_id, target_id)
    except TelegramAPIError:
        await message.answer("این کاربر عضو گروه نیست یا شناسه معتبر نیست."); return
    key = f"guardian:{chat_id}:admins"
    if cmd == "add_admin":
        await redis.sadd(key, str(target_id))
        await message.answer(f"🛡️ {html.escape(member.user.full_name)} به مدیران نگهبان اضافه شد.")
    else:
        await redis.srem(key, str(target_id))
        await message.answer(f"📉 {html.escape(member.user.full_name)} از مدیران نگهبان عزل شد.")

class GuardianMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        if not isinstance(event, Message) or not group(event.chat):
            return await handler(event, data)
        chat_id = event.chat.id
        values = await settings(chat_id)
        if event.new_chat_members:
            if values["bots"] and await bot_rights(event.bot, chat_id, "can_restrict_members"):
                for member in event.new_chat_members:
                    if member.is_bot and member.id != (await event.bot.get_me()).id:
                        try:
                            await event.bot.ban_chat_member(chat_id, member.id)
                        except TelegramAPIError:
                            pass
            if values["welcome"]:
                for member in event.new_chat_members:
                    if not member.is_bot:
                        await event.answer("👋 به اِلدوریا خوش آمدی، " + html.escape(member.full_name) + "!")
            return await handler(event, data)
        if not event.from_user or event.from_user.is_bot:
            return await handler(event, data)
        content = event.text or event.caption or ""
        if not content or content.startswith("/"):
            return await handler(event, data)
        if await authorized(event.bot, chat_id, event.from_user.id):
            return await handler(event, data)
        violation = False
        if values["links"] and URL.search(content):
            violation = True
        if values["words"]:
            words = await redis.smembers(f"guardian:{chat_id}:words")
            if any(word and word in content.casefold() for word in words):
                violation = True
        if values["spam"]:
            key = (chat_id, event.from_user.id)
            queue = WINDOW[key]
            now = time.monotonic()
            while queue and now - queue[0] > 8:
                queue.popleft()
            queue.append(now)
            if len(queue) >= 6:
                violation = True
        if violation and await bot_rights(event.bot, chat_id, "can_delete_messages"):
            try:
                await event.delete()
                return None
            except TelegramAPIError:
                pass
        return await handler(event, data)
