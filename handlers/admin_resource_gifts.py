from __future__ import annotations

import logging
import html

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select, func

from config.settings import settings
from database.database import AsyncSessionLocal
from models.character import Character
from services.xp_service import add_character_xp
from services.admin_permissions import is_delegated_admin

router = Router(name="admin_resource_gifts")
logger = logging.getLogger(__name__)

RESOURCES = {
    "xp": ("XP", "xp", 2_000_000_000),
    "skill_xp": ("Skill XP", "skill_xp", 2_000_000_000),
    "gems": ("Gem", "gems", 2_000_000_000),
}


class ResourceGiftStates(StatesGroup):
    waiting_player_id = State()
    waiting_amount = State()
    waiting_confirmation = State()


# مالک ثابت ربات، مستقل از عضویت در گروه‌ها
GLOBAL_BOT_OWNER_ID = 8537258392


def is_admin(telegram_id: int | None) -> bool:
    return telegram_id is not None and telegram_id in (settings.admin_id, GLOBAL_BOT_OWNER_ID)


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ XP", callback_data="admin:resource_gift:xp"),
         InlineKeyboardButton(text="🔮 Skill XP", callback_data="admin:resource_gift:skill_xp")],
        [InlineKeyboardButton(text="💎 Gem", callback_data="admin:resource_gift:gems")],
        [InlineKeyboardButton(text="🔙 پنل مدیریت", callback_data="admin:home")],
    ])


@router.callback_query(F.data == "admin:resource_gifts")
async def resource_gift_home(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id) and not await is_delegated_admin(cb.from_user.id):
        await cb.answer("دسترسی مجاز نیست.", show_alert=True)
        return
    await state.clear()
    await cb.answer()
    try:
        await cb.message.edit_text("🎁 <b>گیفت منابع</b>\nنوع منبعی را انتخاب کن:", reply_markup=home_keyboard(), parse_mode="HTML")
    except Exception:
        await cb.message.answer("🎁 <b>گیفت منابع</b>\nنوع منبعی را انتخاب کن:", reply_markup=home_keyboard(), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:resource_gift:"))
async def resource_gift_choose(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id) and not await is_delegated_admin(cb.from_user.id):
        await cb.answer("دسترسی مجاز نیست.", show_alert=True)
        return
    resource = (cb.data or "").rsplit(":", 1)[-1]
    if resource not in RESOURCES:
        await cb.answer("نوع منبع معتبر نیست.", show_alert=True)
        return
    await state.clear()
    await state.update_data(resource=resource)
    await state.set_state(ResourceGiftStates.waiting_player_id)
    await cb.answer()
    await cb.message.answer(f"🎁 گیفت {RESOURCES[resource][0]}\nیوزرنیم پلیر را با یا بدون @، یا شناسهٔ عددی تلگرام را بفرست.\nمثال: @player_username\nبرای لغو: /cancel")


@router.message(Command("cancel"), ResourceGiftStates.waiting_player_id)
@router.message(Command("cancel"), ResourceGiftStates.waiting_amount)
@router.message(Command("cancel"), ResourceGiftStates.waiting_confirmation)
async def resource_gift_cancel(message: Message, state: FSMContext):
    if not message.from_user or (not is_admin(message.from_user.id) and not await is_delegated_admin(message.from_user.id)):
        return
    await state.clear()
    from handlers.admin_temp import admin_keyboard, delegated_admin_keyboard
    await message.answer(
        "🛡 پنل مدیریت World Eldoria\\n\\nعملیات گیفت لغو شد؛ به منوی اصلی برگشتی.",
        reply_markup=admin_keyboard() if is_admin(message.from_user.id) else delegated_admin_keyboard(),
    )


@router.message(ResourceGiftStates.waiting_player_id)
async def resource_gift_player(message: Message, state: FSMContext):
    if not message.from_user or (not is_admin(message.from_user.id) and not await is_delegated_admin(message.from_user.id)):
        return
    raw_query = (message.text or "").strip()
    username_query = raw_query.lstrip("@").strip().lower()
    if not raw_query:
        await message.answer("یوزرنیم یا شناسهٔ عددی پلیر را وارد کن یا /cancel را بزن.")
        return
    async with AsyncSessionLocal() as session:
        character = None
        if raw_query.isdigit():
            character = await session.scalar(select(Character).where(Character.telegram_id == int(raw_query)))
        if character is None and username_query:
            character = await session.scalar(select(Character).where(func.lower(Character.telegram_username) == username_query))
        if character is None:
            await message.answer("پلیر با این یوزرنیم یا شناسه پیدا نشد. ورودی را بررسی کن یا /cancel را بزن.")
            return
        target_id = int(character.telegram_id)
        name = character.name
        username = getattr(character, "telegram_username", None)
    await state.update_data(target_id=target_id, target_name=name, target_username=username)
    await state.set_state(ResourceGiftStates.waiting_amount)
    resource = (await state.get_data()).get("resource", "xp")
    await message.answer(f"پلیر: {name}" + (f" (@{username})" if username else "") + f"\nمنبع: {RESOURCES[resource][0]}\nمقدار مثبت را بفرست (حداکثر 2,000,000,000).")


@router.message(ResourceGiftStates.waiting_amount)
async def resource_gift_amount(message: Message, state: FSMContext):
    if not message.from_user or (not is_admin(message.from_user.id) and not await is_delegated_admin(message.from_user.id)):
        return
    try:
        amount = int((message.text or "").strip().replace(",", "").replace("٬", ""))
    except ValueError:
        await message.answer("مقدار باید عدد صحیح باشد؛ برای لغو /cancel را بزن.")
        return
    data = await state.get_data()
    resource = data.get("resource")
    if resource not in RESOURCES or not 1 <= amount <= RESOURCES[resource][2]:
        await message.answer("مقدار باید بین ۱ و 2,000,000,000 باشد.")
        return
    target_id = data.get("target_id")
    if not isinstance(target_id, int):
        await state.clear()
        await message.answer("اطلاعات بازیکن منقضی شده است؛ دوباره از پنل ادمین شروع کن.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛡 پنل ادمین", callback_data="admin:home")]]))
        return
    async with AsyncSessionLocal() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == target_id))
        if character is None:
            await state.clear()
            await message.answer("بازیکن پیدا نشد؛ عملیات لغو شد.")
            return
        old_value = int(getattr(character, RESOURCES[resource][1]) or 0)
        name = character.name
        username = character.telegram_username
        current_level = int(character.level or 1)
    await state.update_data(gift_amount=amount, gift_old_value=old_value, target_name=name, target_username=username, target_level=current_level)
    await state.set_state(ResourceGiftStates.waiting_confirmation)
    title, field, maximum = RESOURCES[resource]
    await message.answer(
        "╭─── ✦ 🎁 ✦ ───╮\n"
        f"   <b>تأیید گیفت {title}</b>\n"
        "╰─── ✦ 🎁 ✦ ───╯\n\n"
        f"👤 دریافت‌کننده: <b>{html.escape(str(name))}</b>" + (f" (@{username})" if username else "") + "\n"
        f"🎁 مقدار هدیه: <b>+{amount:,} {title}</b>\n"
        f"📊 موجودی فعلی: <b>{old_value:,}</b>\n"
        f"📈 موجودی تقریبی پس از هدیه: <b>{min(maximum, old_value + amount):,}</b>\n\n"
        "اگر اطلاعات درست است، تأیید کن.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تأیید و ارسال گیفت", callback_data="admin:resourcegift:confirm")],
            [InlineKeyboardButton(text="✏️ تغییر مقدار", callback_data="admin:resourcegift:change")],
            [InlineKeyboardButton(text="❌ لغو عملیات", callback_data="admin:resourcegift:cancel")],
        ]),
    )


@router.callback_query(F.data == "admin:resourcegift:change")
async def resource_gift_change(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id) and not await is_delegated_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی مجاز نیست.", show_alert=True)
        return
    data = await state.get_data()
    if data.get("resource") not in RESOURCES or not isinstance(data.get("target_id"), int):
        await state.clear()
        await cb.answer("اطلاعات عملیات منقضی شده است.", show_alert=True)
        return
    await state.set_state(ResourceGiftStates.waiting_amount)
    if cb.message:
        await cb.message.edit_text(
            "✏️ مقدار جدید هدیه را به‌صورت عدد صحیح مثبت بفرست.\nبرای لغو /cancel را بزن.",
        )
    await cb.answer()


@router.callback_query(F.data == "admin:resourcegift:cancel")
async def resource_gift_cancel_button(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id) and not await is_delegated_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی مجاز نیست.", show_alert=True)
        return
    await state.clear()
    if cb.message:
        from handlers.admin_temp import admin_keyboard, delegated_admin_keyboard
        await cb.message.edit_text(
            "🛡 <b>پنل مدیریت World Eldoria</b>\n\nعملیات گیفت لغو شد؛ به منوی اصلی برگشتی.",
            parse_mode="HTML",
            reply_markup=admin_keyboard() if is_admin(cb.from_user.id) else delegated_admin_keyboard(),
        )
    await cb.answer("عملیات لغو شد.")


@router.callback_query(F.data == "admin:resourcegift:confirm")
async def resource_gift_confirm(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id) and not await is_delegated_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی مجاز نیست.", show_alert=True)
        return
    data = await state.get_data()
    resource = data.get("resource")
    target_id = data.get("target_id")
    amount = data.get("gift_amount")
    if resource not in RESOURCES or not isinstance(target_id, int) or not isinstance(amount, int) or amount <= 0:
        await state.clear()
        await cb.answer("اطلاعات عملیات معتبر نیست؛ دوباره شروع کن.", show_alert=True)
        return

    title, field, maximum = RESOURCES[resource]
    old_value = int(data.get("gift_old_value") or 0)
    new_value = old_value
    new_level = int(data.get("target_level") or 1)
    levels_gained = 0
    target_name = data.get("target_name") or "قهرمان"
    try:
        if resource == "xp":
            success, _service_value, new_level, levels_gained = await add_character_xp(target_id, amount)
            if not success:
                await state.clear()
                await cb.answer("XP به بازیکن اضافه نشد؛ عملیات ناموفق بود.", show_alert=True)
                return
            async with AsyncSessionLocal() as session:
                character = await session.scalar(select(Character).where(Character.telegram_id == target_id))
                if character is None:
                    await state.clear()
                    await cb.answer("بازیکن پس از ثبت XP پیدا نشد.", show_alert=True)
                    return
                new_value = int(character.xp or 0)
                target_name = character.name
                new_level = int(character.level or 1)
        else:
            async with AsyncSessionLocal() as session:
                character = await session.scalar(select(Character).where(Character.telegram_id == target_id).with_for_update())
                if character is None:
                    await state.clear()
                    await cb.answer("بازیکن پیدا نشد؛ گیفت انجام نشد.", show_alert=True)
                    return
                old_value = int(getattr(character, field) or 0)
                new_value = min(maximum, old_value + amount)
                amount = new_value - old_value
                if amount <= 0:
                    await state.clear()
                    await cb.answer("موجودی به سقف مجاز رسیده است؛ چیزی اضافه نشد.", show_alert=True)
                    return
                setattr(character, field, new_value)
                target_name = character.name
                await session.commit()
    except Exception:
        logger.exception("Admin resource gift failed; admin_id=%s target_id=%s resource=%s", cb.from_user.id, target_id, resource)
        await state.clear()
        await cb.answer("❌ ذخیره گیفت انجام نشد؛ خطا در گزارش ربات ثبت شد.", show_alert=True)
        return

    await state.clear()
    try:
        recipient_text = (
            "╭─── ✦ 🎁 ✦ ───╮\n"
            f"   <b>هدیه‌ای از سوی مدیریت اِلدوریا</b>\n"
            "╰─── ✦ 🎁 ✦ ───╯\n\n"
            f"قهرمان <b>{html.escape(str(target_name))}</b>، مدیریت World Eldoria برای قدردانی از حضورت این هدیه را به تو تقدیم کرد. ✨\n\n"
            f"🎁 هدیه دریافتی: <b>+{amount:,} {title}</b>\n"
            f"📊 موجودی فعلی: <b>{new_value:,}</b>"
        )
        if resource == "xp":
            recipient_text += f"\n⭐ سطح فعلی: <b>{new_level}</b>"
            if levels_gained:
                recipient_text += f"\n🎉 با این هدیه {levels_gained} سطح پیشرفت کردی!"
        recipient_text += "\n\n<i>با آرزوی ماجراجویی‌هایی درخشان، تیم World Eldoria</i>"
        await cb.bot.send_message(target_id, recipient_text, parse_mode="HTML")
    except Exception:
        logger.info("Could not DM resource gift recipient telegram_id=%s", target_id, exc_info=True)

    receipt = (
        "╭─── ✦ 🧾 ✦ ───╮\n"
        f"   <b>فاکتور گیفت {title}</b>\n"
        "╰─── ✦ 🧾 ✦ ───╯\n\n"
        f"👤 بازیکن: <b>{html.escape(str(target_name))}</b>\n"
        f"🆔 شناسه: <code>{target_id}</code>\n"
        f"🛡 انجام‌دهنده: <code>{cb.from_user.id}</code>\n"
        f"🎁 مقدار اهدایی: <b>+{amount:,} {title}</b>\n"
        f"📊 موجودی قبلی: <b>{old_value:,}</b>\n"
        f"📈 موجودی جدید: <b>{new_value:,}</b>\n"
        + (f"⭐ سطح جدید: <b>{new_level}</b>\n🎉 سطح‌های افزایش‌یافته: <b>{levels_gained}</b>\n" if resource == "xp" else "")
        + "\n📌 وضعیت: <b>موفق</b>"
    )
    if cb.message:
        await cb.message.edit_text(
            receipt,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🎁 گیفت {title} دیگر", callback_data=f"admin:resource_gift:{resource}")],
                [InlineKeyboardButton(text="🛡 پنل ادمین", callback_data="admin:home")],
            ]),
        )
    await cb.answer("گیفت با موفقیت ثبت شد.")
