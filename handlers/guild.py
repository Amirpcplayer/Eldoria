from __future__ import annotations

import html
import json
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.redis import redis
from middlewares.panel_owner import protect_keyboard
from services.guild_service import (
    GUILD_DONATION_MIN,
    browse_guilds,
    claim_guild_leader_reward,
    create_guild,
    donate_guild_gold,
    disband_guild,
    get_guild_for_player,
    guild_members,
    join_guild,
    leave_guild,
)

router = Router(name="guild")
logger = logging.getLogger(__name__)
FLOW_PREFIX = "eldoria:guild:flow:"
FLOW_TTL = 900


def _key(user_id: int) -> str:
    return f"{FLOW_PREFIX}{user_id}"


async def _get_flow(user_id: int) -> dict | None:
    raw = await redis.get(_key(user_id))
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        await redis.delete(_key(user_id))
        return None
    return value if isinstance(value, dict) else None


async def _set_flow(user_id: int, stage: str, **data) -> None:
    await redis.set(_key(user_id), json.dumps({"stage": stage, **data}, ensure_ascii=False), ex=FLOW_TTL)


async def _clear_flow(user_id: int) -> None:
    await redis.delete(_key(user_id))


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def guild_home_keyboard(has_guild: bool, is_owner: bool = False) -> InlineKeyboardMarkup:
    if has_guild:
        rows = [
            [_btn("📜 اطلاعات گیلد", "guild:info"), _btn("👥 اعضای گیلد", "guild:members")],
            [_btn("🏆 رتبه‌بندی گیلدها", "guild:rankings")],
            [_btn("💰 کمک به خزانه", "guild:donate")],
            [_btn("👑 پاداش روزانهٔ رهبر", "guild:leader_reward")],
            *([[_btn("🗑️ حذف کامل گیلد", "guild:disband")]] if is_owner else []),
            [_btn("🚪 خروج از گیلد", "guild:leave")],
        ]
    else:
        rows = [
            [_btn("🏰 ساخت گیلد", "guild:create")],
            [_btn("🔎 یافتن گیلدها", "guild:rankings")],
            [_btn("🔗 پیوستن با شناسه", "guild:join")],
        ]
    rows.append([_btn("🔄 به‌روزرسانی", "menu:guild"), _btn("🏠 منوی اصلی", "menu:back")])
    return _keyboard(rows)


async def _show(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    """نمایش پنل گیلد؛ دکمه‌های هر پنل فقط برای بازکنندهٔ همان پنل فعال‌اند."""
    message = callback.message
    if markup is not None:
        markup = protect_keyboard(markup, callback.from_user.id)
    if message is not None:
        if message.photo:
            # تلگرام caption یک پیام تصویری را نمی‌تواند به متن تبدیل کند.
            try:
                await message.answer(text, reply_markup=markup, parse_mode="HTML")
            except Exception:
                logger.exception("Could not send guild text panel")
        else:
            try:
                await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
            except Exception as exc:
                # در صورت یکسان‌بودن متن، پنل درست است؛ پیام تازه نساز.
                if "message is not modified" not in str(exc).lower():
                    # اگر واقعاً قابل ویرایش نیست، پیام قبلی را حذف کن و بعد جایگزین بساز.
                    try:
                        await message.delete()
                    except Exception:
                        logger.warning("Could not delete stale guild panel", exc_info=True)
                    try:
                        await message.answer(text, reply_markup=markup, parse_mode="HTML")
                    except Exception:
                        logger.exception("Could not replace guild panel")
    try:
        await callback.answer()
    except Exception:
        pass


async def _home(callback: CallbackQuery, notice: str = "") -> None:
    user_id = callback.from_user.id
    guild = await get_guild_for_player(user_id)
    if not guild:
        text = "🛡️ <b>تالار گیلدهای اِلدوریا</b>\n\nبه یک انجمن ماجراجویی بپیوند یا گیلد خودت را بساز.\n\n🏰 گیلدها با کمک اعضا تجربه می‌گیرند و با ارتقای سطح، ظرفیت بیشتری پیدا می‌کنند."
    else:
        progress = min(100, int(guild["xp"] * 100 / max(1, guild["next_level_xp"])))
        bar = "🟩" * (progress // 10) + "⬜" * (10 - progress // 10)
        text = (
            "🛡️ <b>تالار گیلد اِلدوریا</b>\n\n"
            f"🏰 <b>{html.escape(guild['name'])}</b>  <code>[{html.escape(guild['tag'])}]</code>\n"
            f"🆔 شناسه: <code>{guild['id']}</code>\n"
            f"⭐ سطح گیلد: <b>{guild['level']}</b>\n"
            f"👥 اعضا: <b>{guild['member_count']}/{guild['max_members']}</b>\n"
            f"✨ تجربه: {guild['xp']:,}/{guild['next_level_xp']:,}\n{bar}\n\n"
            f"{'👑 رهبر گیلد هستی.' if guild['role'] == 'owner' else '🤝 عضو گیلد هستی.'}"
        )
    if notice:
        text = f"{notice}\n\n{text}"
    await _show(callback, text, guild_home_keyboard(bool(guild), bool(guild and guild["role"] == "owner")))


@router.callback_query(F.data == "menu:guild")
async def guild_menu(callback: CallbackQuery) -> None:
    await _clear_flow(callback.from_user.id)
    await _home(callback)


@router.callback_query(F.data == "guild:create")
async def guild_create_start(callback: CallbackQuery) -> None:
    if await get_guild_for_player(callback.from_user.id):
        await _show(callback, "⚠️ هم‌اکنون عضو یک گیلد هستی.", guild_home_keyboard(True))
        return
    await _set_flow(callback.from_user.id, "create_name", chat_id=callback.message.chat.id if callback.message else None)
    await _show(callback, "🏰 <b>ساخت گیلد — مرحلهٔ ۱ از ۲</b>\n\nنام گیلد را بفرست (۲ تا ۴۰ نویسه).\n\nبرای لغو از دکمهٔ زیر استفاده کن.", _keyboard([[_btn("✖️ لغو", "guild:cancel")]]))


@router.callback_query(F.data == "guild:join")
async def guild_join_start(callback: CallbackQuery) -> None:
    if await get_guild_for_player(callback.from_user.id):
        await _show(callback, "⚠️ هم‌اکنون عضو یک گیلد هستی.", guild_home_keyboard(True))
        return
    await _set_flow(callback.from_user.id, "join_id", chat_id=callback.message.chat.id if callback.message else None)
    await _show(callback, "🔗 <b>پیوستن به گیلد</b>\n\nشناسهٔ گیلد را ارسال کن.", _keyboard([[_btn("✖️ لغو", "guild:cancel")]]))


@router.callback_query(F.data == "guild:donate")
async def guild_donate_start(callback: CallbackQuery) -> None:
    if not await get_guild_for_player(callback.from_user.id):
        await _show(callback, "⚠️ برای کمک به خزانه باید عضو گیلد باشی.", guild_home_keyboard(False))
        return
    await _set_flow(callback.from_user.id, "donate_amount", chat_id=callback.message.chat.id if callback.message else None)
    await _show(callback, f"💰 <b>کمک به خزانهٔ گیلد</b>\n\nمقدار طلا را به عدد ارسال کن. حداقل کمک: {GUILD_DONATION_MIN:,} طلا.\nهر ۱ طلا برابر ۱ تجربهٔ گیلد است؛ کمک‌ها قابل بازگشت نیستند.", _keyboard([[_btn("✖️ لغو", "guild:cancel")]]))


@router.callback_query(F.data == "guild:cancel")
async def guild_cancel(callback: CallbackQuery) -> None:
    await _clear_flow(callback.from_user.id)
    await _home(callback, "عملیات لغو شد.")


@router.message(F.text)
async def guild_text_flow(message: Message) -> None:
    if not message.from_user or not message.text or message.text.strip().startswith("/"):
        return
    user_id = message.from_user.id
    state = await _get_flow(user_id)
    if not state or state.get("chat_id") != message.chat.id:
        return
    value = message.text.strip()
    stage = state.get("stage")
    if stage == "create_name":
        if not 2 <= len(" ".join(value.split())) <= 40:
            await message.answer("⚠️ نام گیلد باید بین ۲ تا ۴۰ نویسه باشد. دوباره ارسال کن.")
            return
        await _set_flow(user_id, "create_tag", name=" ".join(value.split()), chat_id=message.chat.id)
        await message.answer("🏷️ <b>مرحلهٔ ۲ از ۲</b>\n\nتگ کوتاه گیلد را با حروف و اعداد انگلیسی بفرست (۲ تا ۸ نویسه).\nمثال: ELDORIA", parse_mode="HTML", reply_markup=protect_keyboard(_keyboard([[_btn("✖️ لغو", "guild:cancel")]]), user_id))
        return
    if stage == "create_tag":
        await _clear_flow(user_id)
        success, result = await create_guild(user_id, str(state.get("name") or ""), value)
        await message.answer(("✅ " if success else "⚠️ ") + html.escape(result), parse_mode="HTML", reply_markup=protect_keyboard(guild_home_keyboard(success, success), user_id))
        return
    if stage == "join_id":
        try:
            guild_id = int(value)
        except ValueError:
            await message.answer("⚠️ شناسه باید عدد باشد. دوباره ارسال کن.")
            return
        await _clear_flow(user_id)
        success, result = await join_guild(user_id, guild_id)
        await message.answer(("✅ " if success else "⚠️ ") + html.escape(result), parse_mode="HTML", reply_markup=protect_keyboard(guild_home_keyboard(success, False), user_id))
        return
    if stage == "donate_amount":
        try:
            amount = int(value.replace(",", "").replace("٬", ""))
        except ValueError:
            await message.answer("⚠️ مبلغ باید عدد صحیح باشد. دوباره ارسال کن.")
            return
        if amount <= 0 or amount > 2_000_000_000:
            await message.answer("⚠️ مبلغ واردشده معتبر نیست.")
            return
        await _clear_flow(user_id)
        success, result = await donate_guild_gold(user_id, amount)
        await message.answer(("✅ " if success else "⚠️ ") + html.escape(result), parse_mode="HTML", reply_markup=protect_keyboard(guild_home_keyboard(bool(await get_guild_for_player(user_id))), user_id))


@router.callback_query(F.data == "guild:info")
async def guild_info_panel(callback: CallbackQuery) -> None:
    guild = await get_guild_for_player(callback.from_user.id)
    if not guild:
        await _show(callback, "هنوز عضو هیچ گیلدی نیستی.", guild_home_keyboard(False))
        return
    await _show(callback, (
        "📜 <b>پروندهٔ گیلد</b>\n\n"
        f"🏰 {html.escape(guild['name'])} <code>[{html.escape(guild['tag'])}]</code>\n"
        f"🆔 شناسه: <code>{guild['id']}</code>\n"
        f"⭐ سطح: {guild['level']}\n✨ تجربه: {guild['xp']:,}/{guild['next_level_xp']:,}\n"
        f"👥 ظرفیت: {guild['member_count']}/{guild['max_members']}\n"
        f"👑 رهبر: {'شما' if guild['role'] == 'owner' else 'رهبر گیلد'}\n"
        f"📅 ایجاد: {guild['created_at'].strftime('%Y-%m-%d') if guild['created_at'] else 'نامشخص'}"
    ), _keyboard([[_btn("👥 اعضا", "guild:members")], [_btn("🔙 بازگشت", "menu:guild")]]))


@router.callback_query(F.data == "guild:members")
async def guild_members_panel(callback: CallbackQuery) -> None:
    guild, members = await guild_members(callback.from_user.id)
    if not guild:
        await _show(callback, "هنوز عضو هیچ گیلدی نیستی.", guild_home_keyboard(False))
        return
    lines = [f"👥 <b>اعضای {html.escape(guild['name'])}</b>", f"شناسهٔ گیلد: <code>{guild['id']}</code>", ""]
    for i, member in enumerate(members, 1):
        role = "👑 رهبر" if member["role"] == "owner" else "🛡️ عضو"
        name = html.escape(str(member["name"]))
        you = " <i>(شما)</i>" if int(member["telegram_id"]) == callback.from_user.id else ""
        member_id = int(member["telegram_id"])
        username = str(member.get("username") or "").strip().lstrip("@")
        username_text = f"@{html.escape(username)}" if username else "ندارد"
        lines.append(
            f"{i}. {name}{you} — Lv.{member['level']} · {role}\n"
            f"   👤 تلگرام: <code>{username_text}</code> · "
            f"🆔 شناسه عددی: <code>{member_id}</code>"
        )
    await _show(callback, "\n".join(lines), _keyboard([[_btn("🔙 بازگشت", "menu:guild")]]))


@router.callback_query(F.data == "guild:rankings")
async def guild_rankings(callback: CallbackQuery) -> None:
    guilds = await browse_guilds(10)
    lines = ["🏆 <b>برترین گیلدهای اِلدوریا</b>", ""]
    if not guilds:
        lines.append("هنوز گیلدی ساخته نشده است.")
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, g in enumerate(guilds, 1):
            mark = medals[i - 1] if i <= 3 else f"{i}."
            lines.append(f"{mark} <b>{html.escape(g['name'])}</b> <code>[{html.escape(g['tag'])}]</code>")
            lines.append(f"   ⭐ سطح {g['level']} · 👥 {g['member_count']}/{g['max_members']} · ✨ {g['xp']:,} XP · 🆔 <code>{g['id']}</code>")
    await _show(callback, "\n".join(lines), _keyboard([[_btn("🔗 پیوستن با شناسه", "guild:join")], [_btn("🔙 بازگشت", "menu:guild")]]))


@router.callback_query(F.data == "guild:leader_reward")
async def guild_leader_reward(callback: CallbackQuery) -> None:
    success, result = await claim_guild_leader_reward(callback.from_user.id)
    await _home(callback, ("✅ " if success else "⚠️ ") + html.escape(result))


@router.callback_query(F.data == "guild:leave")
async def guild_leave_confirm(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    guild = await get_guild_for_player(user_id)
    if not guild:
        await _show(callback, "عضو هیچ گیلدی نیستی.", guild_home_keyboard(False))
        return
    if guild["role"] == "owner" and guild["member_count"] > 1:
        _, members = await guild_members(user_id)
        rows = [[_btn(f"👑 {str(m['name'])[:28]}", f"guild:leave:leader:{int(m['telegram_id'])}")]
                for m in members if int(m["telegram_id"]) != user_id]
        rows.append([_btn("🔙 انصراف", "menu:guild")])
        await _show(callback, "👑 <b>انتقال رهبری و خروج</b>\n\nیکی از اعضا را انتخاب کن؛ رهبری گیلد به او منتقل می‌شود و سپس از گیلد خارج می‌شوی.", _keyboard(rows))
        return
    warning = "چون تنها عضو گیلد هستی، با خروج گیلد نیز حذف می‌شود." if guild["role"] == "owner" else "از گیلد خارج خواهی شد؛ این عمل قابل بازگشت خودکار نیست."
    await _show(callback, f"🚪 <b>خروج از گیلد</b>\n\n{warning}\n\nآیا مطمئنی؟", _keyboard([[_btn("✅ تأیید خروج", "guild:leave:confirm")], [_btn("❌ انصراف", "menu:guild")]]))


@router.callback_query(F.data == "guild:leave:confirm")
async def guild_leave_do(callback: CallbackQuery) -> None:
    success, result = await leave_guild(callback.from_user.id)
    await _home(callback, ("✅ " if success else "⚠️ ") + html.escape(result))


@router.callback_query(F.data.startswith("guild:leave:leader:"))
async def guild_leave_with_transfer(callback: CallbackQuery) -> None:
    try:
        successor_id = int(callback.data.rsplit(":", 1)[1])
    except (TypeError, ValueError, AttributeError):
        await callback.answer("عضو انتخاب‌شده معتبر نیست.", show_alert=True)
        return
    success, result = await leave_guild(callback.from_user.id, successor_id)
    await _home(callback, ("✅ " if success else "⚠️ ") + html.escape(result))


@router.callback_query(F.data == "guild:disband")
async def guild_disband_start(callback: CallbackQuery) -> None:
    guild = await get_guild_for_player(callback.from_user.id)
    if not guild or guild["role"] != "owner":
        await _show(callback, "⛔ فقط رهبر گیلد می‌تواند آن را حذف کند.", guild_home_keyboard(bool(guild), False))
        return
    await _show(callback, "🗑️ <b>حذف کامل گیلد</b>\n\nاین کار گیلد و عضویت تمام اعضا را حذف می‌کند و قابل بازگشت نیست. مطمئنی؟", _keyboard([
        [_btn("🗑️ بله، گیلد حذف شود", "guild:disband:confirm")],
        [_btn("❌ انصراف", "menu:guild")],
    ]))


@router.callback_query(F.data == "guild:disband:confirm")
async def guild_disband_do(callback: CallbackQuery) -> None:
    success, result = await disband_guild(callback.from_user.id)
    await _home(callback, ("✅ " if success else "⚠️ ") + html.escape(result))
