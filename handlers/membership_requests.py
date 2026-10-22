from __future__ import annotations

import html
import json
import logging
import secrets

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.bot import bot
from database.redis import redis
from services.party_service import get_party_by_id, get_party_details, join_party
from services.guild_service import get_guild_by_id, get_guild_for_player, join_guild

router = Router(name="membership_requests")
logger = logging.getLogger(__name__)
TTL = 86400


def public_id(kind: str, number: int) -> str:
    return f"{'PTY' if kind == 'party' else 'GLD'}-{number:04d}"


def parse_id(value: str, kind: str) -> int | None:
    value = value.strip().upper()
    prefix = "PTY-" if kind == "party" else "GLD-"
    if value.startswith(prefix):
        value = value[len(prefix):]
    if not value.isdecimal():
        return None
    number = int(value)
    return number if number > 0 else None


def _key(token: str) -> str:
    return f"eldoria:membership:request:{token}"


async def request_membership(kind: str, user_id: int, target_id: int) -> tuple[bool, str]:
    if kind not in ("party", "guild"):
        return False, "نوع درخواست نامعتبر است."
    current = await (get_party_details(user_id) if kind == "party" else get_guild_for_player(user_id))
    if current:
        return False, f"قبلاً عضو «{current['name']}» هستی."
    target = await (get_party_by_id(target_id) if kind == "party" else get_guild_by_id(target_id))
    if not target:
        return False, "گروه موردنظر پیدا نشد."
    if kind == "party" and target.get("status") != "open":
        return False, "این پارتی بسته شده است."
    if int(target["member_count"]) >= int(target["max_members"]):
        return False, "ظرفیت این گروه تکمیل شده است."
    leader_id = int(target["leader_telegram_id"] if kind == "party" else target["owner_telegram_id"])
    if leader_id == user_id:
        return False, "خودت رهبر این گروه هستی."
    token = secrets.token_urlsafe(12)
    key = _key(token)
    await redis.set(key, json.dumps({"kind": kind, "user": user_id, "target": target_id, "leader": leader_id}), ex=TTL)
    try:
        chat = await bot.get_chat(user_id)
        player_name = " ".join(x for x in (chat.first_name, chat.last_name) if x) or str(user_id)
    except Exception:
        player_name = str(user_id)
    label = "پارتی" if kind == "party" else "گیلد"
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ تأیید", callback_data=f"membership:yes:{token}"),
        InlineKeyboardButton(text="❌ رد", callback_data=f"membership:no:{token}"),
    ]])
    try:
        await bot.send_message(
            leader_id,
            f"📨 <b>درخواست عضویت {label}</b>\\n\\n"
            f"👤 <a href=\"tg://user?id={user_id}\">{html.escape(player_name)}</a>\\n"
            f"🆔 بازیکن: <code>{user_id}</code>\\n"
            f"🏷️ {html.escape(target['name'])} · <code>{public_id(kind, target_id)}</code>\\n\\n"
            "این درخواست تا ۲۴ ساعت معتبر است.",
            reply_markup=markup, parse_mode="HTML",
        )
    except Exception:
        await redis.delete(key)
        logger.exception("Could not deliver membership request to leader")
        return False, "ارسال درخواست به پی‌وی رهبر ممکن نشد؛ رهبر باید ابتدا ربات را استارت کند."
    return True, "درخواست به پی‌وی رهبر ارسال شد؛ تا تأیید او عضو نمی‌شوی."


@router.callback_query(F.data.startswith("membership:"))
async def decide_membership(callback: CallbackQuery) -> None:
    try:
        _, action, token = (callback.data or "").split(":", 2)
    except ValueError:
        await callback.answer("درخواست نامعتبر است.", show_alert=True)
        return
    raw = await redis.get(_key(token))
    if not raw:
        await callback.answer("این درخواست منقضی شده یا قبلاً بررسی شده است.", show_alert=True)
        return
    data = json.loads(raw)
    if int(data["leader"]) != callback.from_user.id:
        await callback.answer("فقط رهبر دریافت‌کننده می‌تواند تصمیم بگیرد.", show_alert=True)
        return
    lock = f"{_key(token)}:lock"
    if not await redis.set(lock, "1", nx=True, ex=45):
        await callback.answer("درخواست در حال بررسی است.", show_alert=True)
        return
    try:
        raw = await redis.get(_key(token))
        if not raw:
            await callback.answer("این درخواست قبلاً بررسی شده است.", show_alert=True)
            return
        kind, user_id, target_id = data["kind"], int(data["user"]), int(data["target"])
        target = await (get_party_by_id(target_id) if kind == "party" else get_guild_by_id(target_id))
        leader_field = "leader_telegram_id" if kind == "party" else "owner_telegram_id"
        if not target or int(target[leader_field]) != callback.from_user.id:
            result = "رهبری گروه تغییر کرده یا گروه حذف شده است."
        elif action == "no":
            result = "درخواست عضویت رد شد."
            try:
                await bot.send_message(user_id, f"❌ درخواست عضویت در «{html.escape(target['name'])}» رد شد.", parse_mode="HTML")
            except Exception:
                logger.info("Could not notify rejected applicant %s", user_id)
        elif action == "yes":
            current = await (get_party_details(user_id) if kind == "party" else get_guild_for_player(user_id))
            if current:
                result = f"⚠️ بازیکن قبلاً عضو «{current['name']}» شده است؛ عضویت جدید انجام نشد."
            else:
                success, result = await (join_party(user_id, target_id) if kind == "party" else join_guild(user_id, target_id))
                if not success:
                    current = await (get_party_details(user_id) if kind == "party" else get_guild_for_player(user_id))
                    if current:
                        result = f"⚠️ بازیکن قبلاً عضو «{current['name']}» شده است؛ عضویت جدید انجام نشد."
                if success:
                    try:
                        await bot.send_message(user_id, "✅ " + html.escape(result), parse_mode="HTML")
                    except Exception:
                        logger.info("Could not notify accepted applicant %s", user_id)
        else:
            await callback.answer("عملیات نامعتبر است.", show_alert=True)
            return
        await redis.delete(_key(token))
        if callback.message:
            await callback.message.edit_text(html.escape(result), parse_mode="HTML")
        await callback.answer()
    finally:
        await redis.delete(lock)
