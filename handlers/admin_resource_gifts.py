from __future__ import annotations

import logging

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
from services.admin_permissions import is_fanart_admin

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
    if not is_admin(cb.from_user.id) and not await is_fanart_admin(cb.from_user.id):
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
    if not is_admin(cb.from_user.id) and not await is_fanart_admin(cb.from_user.id):
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
async def resource_gift_cancel(message: Message, state: FSMContext):
    if not message.from_user or (not is_admin(message.from_user.id) and not await is_fanart_admin(message.from_user.id)):
        return
    await state.clear()
    await message.answer("عملیات گیفت لغو شد.")


@router.message(ResourceGiftStates.waiting_player_id)
async def resource_gift_player(message: Message, state: FSMContext):
    if not message.from_user or (not is_admin(message.from_user.id) and not await is_fanart_admin(message.from_user.id)):
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
    if not message.from_user or (not is_admin(message.from_user.id) and not await is_fanart_admin(message.from_user.id)):
        return
    try:
        amount = int((message.text or "").strip().replace(",", ""))
    except ValueError:
        await message.answer("مقدار باید عدد صحیح باشد.")
        return
    data = await state.get_data()
    resource = data.get("resource")
    if resource not in RESOURCES or not 1 <= amount <= RESOURCES[resource][2]:
        await message.answer("مقدار باید بین ۱ و 2,000,000,000 باشد.")
        return
    _, field, maximum = RESOURCES[resource]
    levels_gained = 0
    try:
        if resource == "xp":
            # XP must go through the XP service so all level-up thresholds, stats,
            # titles and level-up notifications are applied consistently.
            success, new_value, new_level, levels_gained = await add_character_xp(int(data["target_id"]), amount)
            if not success:
                await state.clear()
                await message.answer("پلیر پیدا نشد یا XP قابل اعمال نبود؛ گیفت انجام نشد.")
                return
            async with AsyncSessionLocal() as session:
                character = await session.scalar(select(Character).where(Character.telegram_id == int(data["target_id"])))
                if character is None:
                    await state.clear()
                    await message.answer("پلیر پس از ثبت XP پیدا نشد؛ وضعیت دیتابیس را بررسی کن.")
                    return
                new_value = int(character.xp or 0)
                new_level = int(character.level or 1)
                name = character.name
        else:
            async with AsyncSessionLocal() as session:
                character = await session.scalar(select(Character).where(Character.telegram_id == int(data["target_id"])).with_for_update())
                if character is None:
                    await state.clear()
                    await message.answer("پلیر دیگر پیدا نشد؛ عملیات لغو شد.")
                    return
                old_value = int(getattr(character, field) or 0)
                new_value = min(maximum, old_value + amount)
                actual = new_value - old_value
                setattr(character, field, new_value)
                name = character.name
                await session.commit()
                amount = actual
    except Exception:
        logger.exception("Admin resource gift failed; admin_id=%s target_id=%s resource=%s", message.from_user.id, data.get("target_id"), resource)
        await message.answer("❌ ذخیرهٔ گیفت انجام نشد؛ خطا در گزارش ربات ثبت شد.")
        await state.clear()
        return
    await state.clear()
    if resource == "xp":
        level_text = f"\nلول فعلی: {new_level}" + (f"\n🎉 تعداد لول‌های گرفته‌شده: +{levels_gained}" if levels_gained else "\nاین مقدار XP برای لول بعدی کافی نبود.")
        await message.answer(f"✅ گیفت XP انجام شد.\nپلیر: {name}\nمقدار افزوده‌شده: +{amount:,} XP\nXP باقی‌مانده: {new_value:,}{level_text}")
    else:
        await message.answer(f"✅ گیفت انجام شد.\nپلیر: {name}\nمنبع: {RESOURCES[resource][0]}\nمقدار افزوده‌شده: +{amount:,}\nموجودی جدید: {new_value:,}")
    try:
        if resource == "xp":
            recipient_text = f"🎁 مدیریت اِلدوریا به تو {amount:,} XP هدیه داد!\nلول فعلی: {new_level}"
            if levels_gained:
                recipient_text += f"\n🎉 تبریک! با این گیفت {levels_gained} لول بالا رفتی!"
            elif new_level >= 100:
                recipient_text += "\nبه حداکثر لول رسیده‌ای."
        else:
            recipient_text = f"🎁 مدیریت اِلدوریا به تو {amount:,} {RESOURCES[resource][0]} هدیه داد!"
        await message.bot.send_message(int(data["target_id"]), recipient_text)
    except Exception:
        logger.debug("Could not notify gift recipient telegram_id=%s", data.get("target_id"), exc_info=True)
