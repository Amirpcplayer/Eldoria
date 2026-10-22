from __future__ import annotations

import html
import json
import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import BaseFilter
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.bot import bot
from database.redis import redis
from middlewares.panel_owner import protect_keyboard
from services.panel_image_service import show_panel
from services.party_service import (
    PARTY_CREATION_COSTS,
    create_party,
    disband_party,
    get_character_by_username,
    get_character_gold,
    get_party_details,
    get_party_members,
    join_party,
    join_party_from_invitation,
    kick_party_member,
    leave_party,
    rename_party,
    upgrade_party,
)

router = Router(name="party")
logger = logging.getLogger(__name__)

PARTY_FLOW_TTL = 1800
PARTY_FLOW_PREFIX = "eldoria:party:flow:"
PARTY_INVITE_PREFIX = "eldoria:party:invite:"
PARTY_INVITE_TTL = 900

MAX_NAME_LENGTH = 40
MAX_TITLE_LENGTH = 40
MAX_DESCRIPTION_LENGTH = 500


# ============================================================
# Redis state
# ============================================================

def _flow_key(telegram_id: int) -> str:
    return f"{PARTY_FLOW_PREFIX}{telegram_id}"


def _invite_key(telegram_id: int) -> str:
    return f"{PARTY_INVITE_PREFIX}{telegram_id}"


async def get_party_flow(telegram_id: int) -> dict[str, Any] | None:
    raw = await redis.get(_flow_key(telegram_id))

    if not raw:
        return None

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")

    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        await redis.delete(_flow_key(telegram_id))
        return None

    return value if isinstance(value, dict) else None


async def set_party_flow(
    telegram_id: int,
    stage: str,
    **data: Any,
) -> dict[str, Any]:
    current = await get_party_flow(telegram_id) or {}
    current.update(data)
    current["stage"] = stage
    current["telegram_id"] = telegram_id

    await redis.set(
        _flow_key(telegram_id),
        json.dumps(current, ensure_ascii=False),
        ex=PARTY_FLOW_TTL,
    )

    return current


async def clear_party_flow(telegram_id: int) -> None:
    await redis.delete(_flow_key(telegram_id))


async def get_party_invitation(telegram_id: int) -> dict | None:
    raw = await redis.get(_invite_key(telegram_id))

    if not raw:
        return None

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")

    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        await redis.delete(_invite_key(telegram_id))
        return None

    return data if isinstance(data, dict) else None


class PartyInputFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.from_user is None or message.text is None:
            return False

        if message.text.strip().startswith("/"):
            return False

        return await get_party_flow(message.from_user.id) is not None


# ============================================================
# Keyboards
# ============================================================

def _button(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
    )


def party_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_button("✖️ لغو عملیات", "party:cancel")]
        ]
    )


def party_main_keyboard(has_party: bool) -> InlineKeyboardMarkup:
    if has_party:
        rows = [
            [_button("👥 اعضای پارتی", "party:members")],
            [_button("⚙️ مدیریت پارتی", "party:manage")],
            [_button("🚪 خروج از پارتی", "party:leave")],
        ]
    else:
        rows = [
            [_button("➕ ساخت پارتی", "party:create")],
            [_button("🔎 پیوستن به پارتی", "party:join")],
        ]

    rows.append([_button("🔄 به‌روزرسانی پارتی", "menu:party")])
    rows.append([_button("🏠 بازگشت به منوی اصلی", "menu:back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def party_capacity_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            _button(
                f"👥 {capacity} نفر — 💰 {cost:,}",
                f"party:capacity:{capacity}",
            )
        ]
        for capacity, cost in PARTY_CREATION_COSTS.items()
    ]

    rows.append([_button("✖️ لغو", "party:cancel")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def party_manage_keyboard(
    details: dict[str, Any],
) -> InlineKeyboardMarkup:
    rows = [
        [_button("✏️ تغییر نام پارتی", "party:rename")],
        [_button("📨 دعوت بازیکن", "party:invite")],
        [_button("👥 مدیریت اعضا", "party:kick:list")],
    ]

    if int(details.get("max_members") or 4) < 10:
        rows.append(
            [_button("⬆️ ارتقای ظرفیت (+۲) — 💰 2,000", "party:upgrade")]
        )

    rows.extend(
        [
            [_button("👥 نمایش اعضا", "party:members")],
            [_button("🗑️ حذف کامل پارتی", "party:disband")],
            [_button("🔙 بازگشت", "menu:party")],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def party_kick_confirm_keyboard(
    target_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_button("✅ ادامه و ثبت دلیل", f"party:kick:yes:{target_id}")],
            [_button("🔙 بازگشت", "party:kick:list")],
        ]
    )


def party_leave_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_button("✅ بله، خارج می‌شوم", "party:leave:yes")],
            [_button("❌ انصراف", "menu:party")],
        ]
    )


def party_invitation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_button("✅ قبول دعوت", "party:invite:accept")],
            [_button("❌ رد دعوت", "party:invite:decline")],
        ]
    )


# ============================================================
# Panel helpers
# ============================================================

async def show_party_panel(
    callback: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await show_panel(
            callback=callback,
            panel_name="party",
            text=text,
            reply_markup=keyboard,
        )
    except Exception:
        logger.exception("Failed to render party panel")
        try:
            await callback.answer(
                "نمایش پنل با خطا مواجه شد.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    try:
        await callback.answer()
    except Exception:
        pass


async def show_party_message(
    message: Message,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> Message:
    owner_id = message.from_user.id if message.from_user else None

    protected_keyboard = (
        protect_keyboard(keyboard, owner_id)
        if keyboard is not None and owner_id is not None
        else keyboard
    )

    return await message.answer(
        text,
        reply_markup=protected_keyboard,
        parse_mode="HTML",
    )


async def show_input_prompt(
    callback: CallbackQuery,
    text: str,
    stage: str,
    **flow_data: Any,
) -> None:
    if callback.message is None:
        await callback.answer(
            "پیام پنل در دسترس نیست.",
            show_alert=True,
        )
        return

    owner_id = callback.from_user.id

    await set_party_flow(
        owner_id,
        stage,
        chat_id=callback.message.chat.id,
        panel_message_id=callback.message.message_id,
        **flow_data,
    )

    await show_party_panel(
        callback,
        text,
        party_cancel_keyboard(),
    )


async def show_input_prompt_from_message(
    message: Message,
    text: str,
    stage: str,
    **flow_data: Any,
) -> None:
    if message.from_user is None:
        return

    owner_id = message.from_user.id

    await set_party_flow(
        owner_id,
        stage,
        chat_id=message.chat.id,
        **flow_data,
    )

    sent = await show_party_message(
        message,
        text,
        party_cancel_keyboard(),
    )

    state = await get_party_flow(owner_id)

    if state is not None:
        state["panel_message_id"] = sent.message_id
        await redis.set(
            _flow_key(owner_id),
            json.dumps(state, ensure_ascii=False),
            ex=PARTY_FLOW_TTL,
        )


def _safe(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


async def _edit_message_or_send(
    message: Message,
    panel_message_id: int | None,
    text: str,
    keyboard: InlineKeyboardMarkup | None,
) -> None:
    owner_id = message.from_user.id if message.from_user else None

    protected_keyboard = (
        protect_keyboard(keyboard, owner_id)
        if keyboard is not None and owner_id is not None
        else keyboard
    )

    if panel_message_id is not None:
        try:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=int(panel_message_id),
                caption=text,
                reply_markup=protected_keyboard,
                parse_mode="HTML",
            )
            return
        except Exception:
            pass

        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=int(panel_message_id),
                text=text,
                reply_markup=protected_keyboard,
                parse_mode="HTML",
            )
            return
        except Exception:
            pass

    await show_party_message(message, text, keyboard)


# ============================================================
# Party panel rendering
# ============================================================

async def render_party(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    details = await get_party_details(telegram_id)

    if not details:
        await show_party_panel(
            callback,
            (
                "🎉 <b>پارتی اِلدوریا</b>\n\n"
                "هنوز عضو هیچ پارتی نیستی.\n"
                "می‌توانی یک پارتی بسازی یا به پارتی دیگری بپیوندی."
            ),
            party_main_keyboard(False),
        )
        return

    members = await get_party_members(details["id"])
    leader_id = int(details["leader_telegram_id"])
    is_leader = leader_id == telegram_id

    lines = [
        "🎉 <b>پارتی اِلدوریا</b>",
        "",
        f"🆔 شناسه: <code>{details['id']}</code>",
        f"🏷️ نام: <b>{_safe(details.get('name'))}</b>",
        f"✨ عنوان: {_safe(details.get('title'))}",
        f"📝 توضیحات: {_safe(details.get('description') or 'بدون توضیحات')}",
        f"👥 ظرفیت: {details.get('member_count', len(members))}"
        f"/{details.get('max_members', 4)}",
        f"👑 رهبر: {'شما' if is_leader else 'بازیکن دیگر'}",
        "",
        "<b>اعضای پارتی:</b>",
    ]

    if not members:
        lines.append("هنوز عضوی ثبت نشده است.")
    else:
        for index, member in enumerate(members, start=1):
            member_id = int(member["telegram_id"])
            member_name = _safe(member.get("name") or "بازیکن")
            role = " 👑" if member_id == leader_id else ""

            if member_id == telegram_id:
                member_name = f"<u>{member_name} (شما)</u>"

            username = str(member.get("username") or "").strip().lstrip("@")
            username_text = f"@{html.escape(username)}" if username else "ندارد"
            lines.append(
                f"{index}. {member_name} — Lv.{member.get('level', 1)}{role}\n"
                f"   👤 تلگرام: <code>{username_text}</code> · "
                f"🆔 شناسه عددی: <code>{member_id}</code>"
            )

    keyboard = (
        party_manage_keyboard(details)
        if is_leader
        else party_main_keyboard(True)
    )

    await show_party_panel(callback, "\n".join(lines), keyboard)


async def render_party_after_input(
    message: Message,
    panel_message_id: int | None,
    notice: str,
) -> None:
    telegram_id = message.from_user.id
    details = await get_party_details(telegram_id)

    if not details:
        await _edit_message_or_send(
            message,
            panel_message_id,
            f"{notice}\n\nعضو هیچ پارتی نیستی.",
            party_main_keyboard(False),
        )
        return

    members = await get_party_members(details["id"])
    leader_id = int(details["leader_telegram_id"])

    lines = [
        f"{notice}",
        "",
        "🎉 <b>پارتی اِلدوریا</b>",
        "",
        f"🆔 شناسه: <code>{details['id']}</code>",
        f"🏷️ نام: <b>{_safe(details.get('name'))}</b>",
        f"✨ عنوان: {_safe(details.get('title'))}",
        f"📝 توضیحات: {_safe(details.get('description') or 'بدون توضیحات')}",
        f"👥 ظرفیت: {details['member_count']}/{details['max_members']}",
        "",
        "<b>اعضای پارتی:</b>",
    ]

    for index, member in enumerate(members, start=1):
        member_id = int(member["telegram_id"])
        role = " 👑" if member_id == leader_id else ""
        member_name = _safe(member.get("name") or "بازیکن")

        if member_id == telegram_id:
            member_name = f"<u>{member_name} (شما)</u>"

        username = str(member.get("username") or "").strip().lstrip("@")
        username_text = f"@{html.escape(username)}" if username else "ندارد"
        lines.append(
            f"{index}. {member_name} — Lv.{member.get('level', 1)}{role}\n"
            f"   👤 تلگرام: <code>{username_text}</code> · "
            f"🆔 شناسه عددی: <code>{member_id}</code>"
        )

    keyboard = (
        party_manage_keyboard(details)
        if leader_id == telegram_id
        else party_main_keyboard(True)
    )

    await _edit_message_or_send(
        message,
        panel_message_id,
        "\n".join(lines),
        keyboard,
    )


@router.callback_query(F.data == "menu:party")
async def party_menu(callback: CallbackQuery) -> None:
    await clear_party_flow(callback.from_user.id)
    await render_party(callback)


# ============================================================
# Create and join flows
# ============================================================

@router.callback_query(F.data == "party:create")
async def party_create_start(callback: CallbackQuery) -> None:
    details = await get_party_details(callback.from_user.id)

    if details:
        await show_party_panel(
            callback,
            "⚠️ تو هم‌اکنون عضو یک پارتی هستی.",
            party_main_keyboard(True),
        )
        return

    await show_input_prompt(
        callback,
        (
            "➕ <b>ساخت پارتی — مرحلهٔ ۱ از ۴</b>\n\n"
            "نام پارتی را وارد کن.\n"
            f"حداکثر طول نام: {MAX_NAME_LENGTH} نویسه."
        ),
        "create_name",
        party_name=None,
        party_title=None,
        party_description=None,
    )


@router.callback_query(F.data == "party:join")
async def party_join_start(callback: CallbackQuery) -> None:
    details = await get_party_details(callback.from_user.id)

    if details:
        await show_party_panel(
            callback,
            "⚠️ تو هم‌اکنون عضو یک پارتی هستی.",
            party_main_keyboard(True),
        )
        return

    await show_input_prompt(
        callback,
        (
            "🔎 <b>پیوستن به پارتی</b>\n\n"
            "شناسهٔ پارتی موردنظر را ارسال کن."
        ),
        "join_party_id",
    )


# ============================================================
# Invite player
# ============================================================

@router.callback_query(F.data == "party:invite")
async def party_invite_start(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    details = await get_party_details(telegram_id)

    if not details:
        await show_party_panel(
            callback,
            "⚠️ عضو هیچ پارتی نیستی.",
            party_main_keyboard(False),
        )
        return

    if int(details["leader_telegram_id"]) != telegram_id:
        await show_party_panel(
            callback,
            "⛔ فقط رهبر پارتی می‌تواند بازیکن دعوت کند.",
            party_main_keyboard(True),
        )
        return

    if int(details["member_count"]) >= int(details["max_members"]):
        await show_party_panel(
            callback,
            "⚠️ ظرفیت پارتی تکمیل شده است؛ ابتدا ظرفیت را ارتقا بده.",
            party_manage_keyboard(details),
        )
        return

    await show_input_prompt(
        callback,
        (
            "📨 <b>دعوت بازیکن به پارتی</b>\n\n"
            "نام کاربری تلگرام بازیکن را ارسال کن.\n"
            "مثال: <code>@playername</code>\n\n"
            "دعوت تا ۱۵ دقیقه معتبر است. بازیکن باید قبلاً "
            "ربات را شروع کرده باشد تا پیام خصوصی دریافت کند."
        ),
        "invite_username",
    )


async def send_party_invitation(
    inviter_id: int,
    username: str,
) -> tuple[bool, str]:
    username = username.strip().lstrip("@").lower()

    if not username or len(username) > 64:
        return False, "نام کاربری معتبر نیست."

    details = await get_party_details(inviter_id)

    if not details:
        return False, "پارتی فعالی پیدا نشد."

    if int(details["leader_telegram_id"]) != inviter_id:
        return False, "فقط رهبر پارتی می‌تواند دعوت ارسال کند."

    if int(details["member_count"]) >= int(details["max_members"]):
        return False, "ظرفیت پارتی تکمیل شده است."

    target = await get_character_by_username(username)

    if target is None:
        return (
            False,
            "بازیکنی با این نام کاربری در شخصیت‌های ثبت‌شده پیدا نشد. "
            "بازیکن باید شخصیت ساخته باشد و نام کاربری‌اش ثبت شده باشد.",
        )

    target_id = int(target["telegram_id"])

    if target_id == inviter_id:
        return False, "نمی‌توانی خودت را دعوت کنی."

    target_party = await get_party_details(target_id)

    if target_party:
        return False, "این بازیکن هم‌اکنون عضو یک پارتی است."

    invite_key = _invite_key(target_id)

    if await redis.get(invite_key):
        return False, "این بازیکن هم‌اکنون یک دعوت فعال دارد."

    invitation = {
        "party_id": int(details["id"]),
        "inviter_id": inviter_id,
        "party_name": str(details["name"]),
    }

    await redis.set(
        invite_key,
        json.dumps(invitation, ensure_ascii=False),
        ex=PARTY_INVITE_TTL,
    )

    keyboard = protect_keyboard(
        party_invitation_keyboard(),
        target_id,
    )

    try:
        await bot.send_message(
            chat_id=target_id,
            text=(
                "📨 <b>دعوت به پارتی اِلدوریا</b>\n\n"
                f"👑 دعوت‌کننده: <code>@{html.escape(username)}</code>\n"
                f"🏷️ نام پارتی: <b>{_safe(details['name'])}</b>\n"
                f"🆔 شناسهٔ پارتی: <code>{details['id']}</code>\n\n"
                "این دعوت تا ۱۵ دقیقه اعتبار دارد. "
                "اگر می‌خواهی عضو شوی، قبول دعوت را بزن."
            ),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception:
        logger.warning(
            "Could not send party invitation to Telegram user %s",
            target_id,
            exc_info=True,
        )
        await redis.delete(invite_key)

        return (
            False,
            "ارسال پیام خصوصی ممکن نشد. بازیکن باید ربات را "
            "شروع کرده باشد و دریافت پیام از ربات برایش مسدود نباشد.",
        )

    return True, f"دعوت برای @{username} ارسال شد."


@router.callback_query(F.data == "party:invite:accept")
async def party_invite_accept(callback: CallbackQuery) -> None:
    target_id = callback.from_user.id
    invitation = await get_party_invitation(target_id)

    if not invitation:
        await callback.answer(
            "این دعوت منقضی شده یا دیگر معتبر نیست.",
            show_alert=True,
        )
        return

    try:
        party_id = int(invitation["party_id"])
        inviter_id = int(invitation["inviter_id"])
    except (KeyError, TypeError, ValueError):
        await redis.delete(_invite_key(target_id))
        await callback.answer("اطلاعات دعوت معتبر نیست.", show_alert=True)
        return

    success, result_message = await join_party_from_invitation(
        telegram_id=target_id,
        party_id=party_id,
        inviter_telegram_id=inviter_id,
    )

    # چه عضویت موفق باشد و چه دعوت دیگر معتبر نباشد، این دعوت مصرف می‌شود.
    await redis.delete(_invite_key(target_id))

    try:
        if callback.message:
            await callback.message.edit_text(
                (
                    f"{'✅' if success else '⚠️'} "
                    f"{html.escape(result_message)}"
                ),
                parse_mode="HTML",
                reply_markup=None,
            )
    except Exception:
        logger.debug("Could not update invitation message", exc_info=True)

    await callback.answer(
        "عضویت انجام شد." if success else "دعوت قابل استفاده نیست.",
        show_alert=not success,
    )

    if success:
        try:
            await bot.send_message(
                inviter_id,
                (
                    "✅ بازیکن دعوت‌شده به پارتی تو پیوست.\n"
                    f"🆔 شناسهٔ پارتی: {party_id}"
                ),
            )
        except Exception:
            logger.debug("Could not notify party leader", exc_info=True)


@router.callback_query(F.data == "party:invite:decline")
async def party_invite_decline(callback: CallbackQuery) -> None:
    target_id = callback.from_user.id
    invitation = await get_party_invitation(target_id)

    await redis.delete(_invite_key(target_id))

    try:
        if callback.message:
            await callback.message.edit_text(
                "❌ دعوت پارتی را رد کردی.",
                reply_markup=None,
            )
    except Exception:
        logger.debug("Could not update declined invitation", exc_info=True)

    await callback.answer("دعوت رد شد.")

    if invitation:
        try:
            inviter_id = int(invitation["inviter_id"])
            await bot.send_message(
                inviter_id,
                "ℹ️ بازیکن دعوت‌شده، دعوت پارتی را رد کرد.",
            )
        except Exception:
            logger.debug("Could not notify party leader", exc_info=True)


# ============================================================
# Text input flow
# ============================================================

@router.message(PartyInputFilter())
async def party_text_input(message: Message) -> None:
    if message.from_user is None or message.text is None:
        return

    telegram_id = message.from_user.id
    text = message.text.strip()
    state = await get_party_flow(telegram_id)

    if not state:
        return

    if state.get("telegram_id") != telegram_id:
        await clear_party_flow(telegram_id)
        return

    if state.get("chat_id") != message.chat.id:
        return

    stage = state.get("stage")

    if stage == "create_name":
        if not text or len(text) > MAX_NAME_LENGTH:
            await show_input_prompt_from_message(
                message,
                f"⚠️ نام باید بین ۱ تا {MAX_NAME_LENGTH} نویسه باشد.",
                "create_name",
            )
            return

        await show_input_prompt_from_message(
            message,
            (
                "➕ <b>ساخت پارتی — مرحلهٔ ۲ از ۴</b>\n\n"
                "عنوان پارتی را وارد کن."
            ),
            "create_title",
            party_name=text,
        )
        return

    if stage == "create_title":
        if not text or len(text) > MAX_TITLE_LENGTH:
            await show_input_prompt_from_message(
                message,
                f"⚠️ عنوان باید بین ۱ تا {MAX_TITLE_LENGTH} نویسه باشد.",
                "create_title",
                party_name=state.get("party_name"),
            )
            return

        await show_input_prompt_from_message(
            message,
            (
                "➕ <b>ساخت پارتی — مرحلهٔ ۳ از ۴</b>\n\n"
                "توضیحات پارتی را وارد کن.\n"
                "اگر توضیحی نمی‌خواهی، فقط «-» ارسال کن."
            ),
            "create_description",
            party_name=state.get("party_name"),
            party_title=text,
        )
        return

    if stage == "create_description":
        description = "" if text == "-" else text

        if len(description) > MAX_DESCRIPTION_LENGTH:
            await show_input_prompt_from_message(
                message,
                f"⚠️ توضیحات نمی‌تواند بیشتر از {MAX_DESCRIPTION_LENGTH} نویسه باشد.",
                "create_description",
                party_name=state.get("party_name"),
                party_title=state.get("party_title"),
            )
            return

        await set_party_flow(
            telegram_id,
            "create_capacity",
            chat_id=message.chat.id,
            party_name=state.get("party_name"),
            party_title=state.get("party_title"),
            party_description=description,
        )

        sent = await show_party_message(
            message,
            (
                "➕ <b>ساخت پارتی — مرحلهٔ ۴ از ۴</b>\n\n"
                "ظرفیت پارتی را انتخاب کن:\n\n"
                "💰 ۴ نفر: ۵٬۰۰۰ طلا\n"
                "💰 ۶ نفر: ۷٬۰۰۰ طلا\n"
                "💰 ۸ نفر: ۹٬۰۰۰ طلا\n"
                "💰 ۱۰ نفر: ۱۱٬۰۰۰ طلا"
            ),
            party_capacity_keyboard(),
        )

        current = await get_party_flow(telegram_id)
        if current:
            current["panel_message_id"] = sent.message_id
            await redis.set(
                _flow_key(telegram_id),
                json.dumps(current, ensure_ascii=False),
                ex=PARTY_FLOW_TTL,
            )
        return

    if stage == "join_party_id":
        try:
            party_id = int(text)
        except ValueError:
            await show_input_prompt_from_message(
                message,
                "⚠️ شناسهٔ پارتی باید عدد باشد.",
                "join_party_id",
            )
            return

        if party_id <= 0:
            await show_input_prompt_from_message(
                message,
                "⚠️ شناسهٔ پارتی معتبر نیست.",
                "join_party_id",
            )
            return

        await clear_party_flow(telegram_id)
        success, result_message = await join_party(telegram_id, party_id)

        await show_party_message(
            message,
            f"{'✅' if success else '⚠️'} {_safe(result_message)}",
            party_main_keyboard(bool(await get_party_details(telegram_id))),
        )
        return

    if stage == "rename_party":
        if not text or len(text) > MAX_NAME_LENGTH:
            await show_input_prompt_from_message(
                message,
                f"⚠️ نام باید بین ۱ تا {MAX_NAME_LENGTH} نویسه باشد.",
                "rename_party",
            )
            return

        await clear_party_flow(telegram_id)

        success, result_message = await rename_party(telegram_id, text)

        await render_party_after_input(
            message,
            state.get("panel_message_id"),
            (
                f"✅ {_safe(result_message)}"
                if success
                else f"⚠️ {_safe(result_message)}"
            ),
        )
        return

    if stage == "invite_username":
        await clear_party_flow(telegram_id)

        success, result_message = await send_party_invitation(
            telegram_id,
            text,
        )

        await render_party_after_input(
            message,
            state.get("panel_message_id"),
            (
                f"✅ {_safe(result_message)}"
                if success
                else f"⚠️ {_safe(result_message)}"
            ),
        )
        return

    if stage == "kick_reason":
        reason = text.strip()
        target_id = state.get("target_id")

        if not reason:
            await show_input_prompt_from_message(
                message,
                "⚠️ دلیل اخراج نمی‌تواند خالی باشد.",
                "kick_reason",
                target_id=target_id,
            )
            return

        if not target_id:
            await clear_party_flow(telegram_id)
            await show_party_message(
                message,
                "⚠️ اطلاعات اخراج معتبر نیست.",
            )
            return

        details = await get_party_details(telegram_id)

        if (
            not details
            or int(details["leader_telegram_id"]) != telegram_id
        ):
            await clear_party_flow(telegram_id)
            await show_party_message(
                message,
                "⛔ فقط رهبر پارتی می‌تواند اعضا را اخراج کند.",
            )
            return

        success, result_message, party_name = await kick_party_member(
            telegram_id,
            int(target_id),
        )

        await clear_party_flow(telegram_id)

        if not success:
            await show_party_message(
                message,
                f"⚠️ {_safe(result_message)}",
            )
            return

        try:
            await bot.send_message(
                chat_id=int(target_id),
                text=(
                    f"⛔ شما از پارتی «{_safe(party_name or details['name'])}» "
                    "اخراج شدید.\n\n"
                    f"📝 دلیل: {_safe(reason)}"
                ),
                parse_mode="HTML",
            )
            notice = "\n\n📨 پیام اخراج برای بازیکن ارسال شد."
        except Exception:
            logger.exception("Could not notify kicked player %s", target_id)
            notice = (
                "\n\n⚠️ بازیکن اخراج شد، اما ارسال پیام خصوصی ممکن نشد."
            )

        await show_party_message(
            message,
            f"✅ {_safe(result_message)}{notice}",
        )


# ============================================================
# Create party: capacity selection
# ============================================================

@router.callback_query(F.data.startswith("party:capacity:"))
async def party_create_capacity(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    state = await get_party_flow(telegram_id)

    if not state or state.get("stage") != "create_capacity":
        await callback.answer(
            "این مرحله منقضی شده است؛ دوباره ساخت پارتی را شروع کن.",
            show_alert=True,
        )
        return

    try:
        capacity = int((callback.data or "").rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("ظرفیت معتبر نیست.", show_alert=True)
        return

    if capacity not in PARTY_CREATION_COSTS:
        await callback.answer("ظرفیت انتخاب‌شده معتبر نیست.", show_alert=True)
        return

    await clear_party_flow(telegram_id)

    success, result_message, party_id = await create_party(
        telegram_id=telegram_id,
        name=str(state.get("party_name") or ""),
        title=str(state.get("party_title") or ""),
        description=str(state.get("party_description") or ""),
        capacity=capacity,
    )

    if not success:
        await show_party_panel(
            callback,
            f"⚠️ {_safe(result_message)}",
            party_main_keyboard(False),
        )
        return

    # موجودی پس از تراکنش دوباره از دیتابیس خوانده می‌شود.
    remaining_gold = await get_character_gold(telegram_id)

    await show_party_panel(
        callback,
        (
            "🎉 <b>پارتی با موفقیت ساخته شد!</b>\n\n"
            f"🆔 شناسهٔ پارتی: <code>{party_id}</code>\n"
            f"🏷️ نام: <b>{_safe(state.get('party_name'))}</b>\n"
            f"✨ عنوان: {_safe(state.get('party_title'))}\n"
            f"👥 ظرفیت: {capacity} نفر\n"
            f"💸 هزینهٔ پرداخت‌شده: {PARTY_CREATION_COSTS[capacity]:,} طلا\n"
            + (
                f"💰 موجودی باقی‌مانده: {remaining_gold:,} طلا\n\n"
                if remaining_gold is not None
                else "\n"
            )
            + "👑 تو رهبر این پارتی هستی."
        ),
        InlineKeyboardMarkup(
            inline_keyboard=[
                [_button("👥 نمایش پارتی", "menu:party")],
            ]
        ),
    )


# ============================================================
# Members and management
# ============================================================

@router.callback_query(F.data == "party:members")
async def party_members_panel(callback: CallbackQuery) -> None:
    await render_party(callback)


@router.callback_query(F.data == "party:manage")
async def party_manage(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    details = await get_party_details(telegram_id)

    if not details:
        await show_party_panel(
            callback,
            "⚠️ تو عضو هیچ پارتی نیستی.",
            party_main_keyboard(False),
        )
        return

    if int(details["leader_telegram_id"]) != telegram_id:
        await show_party_panel(
            callback,
            "⛔ فقط رهبر پارتی به امکانات مدیریت دسترسی دارد.",
            party_main_keyboard(True),
        )
        return

    await show_party_panel(
        callback,
        (
            "⚙️ <b>مدیریت پارتی</b>\n\n"
            f"🏷️ نام: <b>{_safe(details.get('name'))}</b>\n"
            f"👥 ظرفیت: {details['member_count']}/{details['max_members']}\n\n"
            "عملیات موردنظر را انتخاب کن."
        ),
        party_manage_keyboard(details),
    )


@router.callback_query(F.data == "party:rename")
async def party_rename_start(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    details = await get_party_details(telegram_id)

    if (
        not details
        or int(details["leader_telegram_id"]) != telegram_id
    ):
        await show_party_panel(
            callback,
            "⛔ فقط رهبر پارتی می‌تواند نام آن را تغییر دهد.",
            party_main_keyboard(bool(details)),
        )
        return

    await show_input_prompt(
        callback,
        (
            "✏️ <b>تغییر نام پارتی</b>\n\n"
            f"نام فعلی: <b>{_safe(details['name'])}</b>\n"
            f"نام جدید را ارسال کن؛ حداکثر {MAX_NAME_LENGTH} نویسه."
        ),
        "rename_party",
    )


@router.callback_query(F.data == "party:upgrade")
async def party_upgrade(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    details = await get_party_details(telegram_id)

    if not details:
        await show_party_panel(
            callback,
            "⚠️ تو عضو هیچ پارتی نیستی.",
            party_main_keyboard(False),
        )
        return

    if int(details["leader_telegram_id"]) != telegram_id:
        await show_party_panel(
            callback,
            "⛔ فقط رهبر پارتی می‌تواند ظرفیت را ارتقا دهد.",
            party_main_keyboard(True),
        )
        return

    success, result_message = await upgrade_party(telegram_id)
    updated_details = await get_party_details(telegram_id)

    await show_party_panel(
        callback,
        (
            f"{'✅' if success else '⚠️'} {_safe(result_message)}\n\n"
            + (
                f"👥 ظرفیت فعلی: {updated_details['max_members']} نفر"
                if updated_details
                else ""
            )
        ),
        party_manage_keyboard(updated_details)
        if updated_details
        else party_main_keyboard(False),
    )


# ============================================================
# Kick member
# ============================================================

@router.callback_query(F.data == "party:kick:list")
async def party_kick_list(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    details = await get_party_details(telegram_id)

    if (
        not details
        or int(details["leader_telegram_id"]) != telegram_id
    ):
        await show_party_panel(
            callback,
            "⛔ فقط رهبر پارتی می‌تواند اعضا را اخراج کند.",
            party_main_keyboard(bool(details)),
        )
        return

    members = await get_party_members(details["id"])
    rows = []

    for member in members:
        member_id = int(member["telegram_id"])

        if member_id == telegram_id:
            continue

        rows.append(
            [
                _button(
                    f"🚫 {str(member.get('name') or 'بازیکن')[:30]} "
                    f"— Lv.{member.get('level', 1)}",
                    f"party:kick:confirm:{member_id}",
                )
            ]
        )

    rows.append([_button("🔙 بازگشت", "party:manage")])

    text = (
        "👥 در حال حاضر عضو دیگری در پارتی وجود ندارد."
        if len(rows) == 1
        else "🚫 <b>مدیریت اعضای پارتی</b>\n\nبازیکن موردنظر را انتخاب کن."
    )

    await show_party_panel(
        callback,
        text,
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("party:kick:confirm:"))
async def party_kick_confirm(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    details = await get_party_details(telegram_id)

    if (
        not details
        or int(details["leader_telegram_id"]) != telegram_id
    ):
        await callback.answer(
            "فقط رهبر پارتی می‌تواند اعضا را اخراج کند.",
            show_alert=True,
        )
        return

    try:
        target_id = int((callback.data or "").rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("شناسهٔ بازیکن معتبر نیست.", show_alert=True)
        return

    if target_id == telegram_id:
        await callback.answer("نمی‌توانی خودت را اخراج کنی.", show_alert=True)
        return

    members = await get_party_members(details["id"])
    target = next(
        (
            member for member in members
            if int(member["telegram_id"]) == target_id
        ),
        None,
    )

    if target is None:
        await show_party_panel(
            callback,
            "⚠️ این بازیکن دیگر عضو پارتی نیست.",
            party_manage_keyboard(details),
        )
        return

    await show_party_panel(
        callback,
        (
            "⚠️ <b>تأیید اخراج عضو</b>\n\n"
            f"👤 بازیکن: <b>{_safe(target.get('name') or 'بازیکن')}</b>\n"
            f"🆔 شناسه: <code>{target_id}</code>\n\n"
            "برای ادامه، دلیل اخراج را وارد خواهی کرد."
        ),
        party_kick_confirm_keyboard(target_id),
    )


@router.callback_query(F.data.startswith("party:kick:yes:"))
async def party_kick_reason_start(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    details = await get_party_details(telegram_id)

    if (
        not details
        or int(details["leader_telegram_id"]) != telegram_id
    ):
        await callback.answer(
            "فقط رهبر پارتی می‌تواند اعضا را اخراج کند.",
            show_alert=True,
        )
        return

    try:
        target_id = int((callback.data or "").rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("شناسهٔ بازیکن معتبر نیست.", show_alert=True)
        return

    members = await get_party_members(details["id"])

    if not any(int(m["telegram_id"]) == target_id for m in members):
        await show_party_panel(
            callback,
            "⚠️ این بازیکن دیگر عضو پارتی نیست.",
            party_manage_keyboard(details),
        )
        return

    await show_input_prompt(
        callback,
        (
            "📝 <b>دلیل اخراج</b>\n\n"
            "دلیل اخراج این بازیکن را بنویس."
        ),
        "kick_reason",
        target_id=target_id,
    )


# ============================================================
# Leave party
# ============================================================

@router.callback_query(F.data == "party:leave")
async def party_leave_start(callback: CallbackQuery) -> None:
    details = await get_party_details(callback.from_user.id)

    if not details:
        await show_party_panel(
            callback,
            "⚠️ تو عضو هیچ پارتی نیستی.",
            party_main_keyboard(False),
        )
        return

    is_leader = (
        int(details["leader_telegram_id"]) == callback.from_user.id
    )

    if is_leader and int(details.get("member_count", 1)) > 1:
        members = await get_party_members(int(details["id"]))
        rows = [[_button(f"👑 {str(m.get('name') or 'بازیکن')[:30]}", f"party:leave:leader:{int(m['telegram_id'])}")]
                for m in members if int(m["telegram_id"]) != callback.from_user.id]
        rows.append([_button("🔙 انصراف", "menu:party")])
        await show_party_panel(callback, "👑 <b>انتقال رهبری و خروج</b>\n\nیکی از اعضا را انتخاب کن تا رهبری به او منتقل شود و سپس از پارتی خارج شوی.", InlineKeyboardMarkup(inline_keyboard=rows))
        return
    await show_party_panel(
        callback,
        "🚪 <b>خروج از پارتی</b>\n\nبا تأیید تو پارتی بسته می‌شود." if is_leader else "🚪 <b>خروج از پارتی</b>\n\nآیا مطمئنی؟",
        InlineKeyboardMarkup(inline_keyboard=[
            [_button("✅ تأیید خروج", "party:leave:yes")],
            [_button("❌ انصراف", "menu:party")],
        ]),
    )


@router.callback_query(F.data == "party:leave:yes")
async def party_leave_confirmed(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    success, result_message = await leave_party(telegram_id)
    await clear_party_flow(telegram_id)
    details = await get_party_details(telegram_id)
    await show_party_panel(callback, f"{'✅' if success else '⚠️'} {_safe(result_message)}", party_main_keyboard(bool(details)))


@router.callback_query(F.data.startswith("party:leave:leader:"))
async def party_leave_with_transfer(callback: CallbackQuery) -> None:
    try:
        successor_id = int(callback.data.rsplit(":", 1)[1])
    except (TypeError, ValueError, AttributeError):
        await callback.answer("عضو انتخاب‌شده معتبر نیست.", show_alert=True)
        return
    success, result_message = await leave_party(callback.from_user.id, successor_id)
    await clear_party_flow(callback.from_user.id)
    details = await get_party_details(callback.from_user.id)
    await show_party_panel(callback, f"{'✅' if success else '⚠️'} {_safe(result_message)}", party_main_keyboard(bool(details)))


@router.callback_query(F.data == "party:disband")
async def party_disband_start(callback: CallbackQuery) -> None:
    details = await get_party_details(callback.from_user.id)
    if not details or int(details["leader_telegram_id"]) != callback.from_user.id:
        await show_party_panel(callback, "⛔ فقط رهبر پارتی می‌تواند آن را حذف کند.", party_main_keyboard(bool(details)))
        return
    await show_party_panel(callback, "🗑️ <b>حذف کامل پارتی</b>\n\nاین کار پارتی را می‌بندد و همهٔ اعضا را از آن خارج می‌کند. مطمئنی؟", InlineKeyboardMarkup(inline_keyboard=[
        [_button("🗑️ بله، حذف شود", "party:disband:yes")],
        [_button("❌ انصراف", "menu:party")],
    ]))


@router.callback_query(F.data == "party:disband:yes")
async def party_disband_confirmed(callback: CallbackQuery) -> None:
    success, result_message = await disband_party(callback.from_user.id)
    await clear_party_flow(callback.from_user.id)
    await show_party_panel(callback, f"{'✅' if success else '⚠️'} {_safe(result_message)}", party_main_keyboard(False))


# ============================================================
# Cancel
# ============================================================

@router.callback_query(F.data == "party:cancel")
async def party_cancel(callback: CallbackQuery) -> None:
    await clear_party_flow(callback.from_user.id)
    await render_party(callback)