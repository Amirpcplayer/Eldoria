from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config.settings import settings
from services.emoji_manager_service import (
    ALL_BUTTONS, MAIN_BUTTONS, INTERNAL_BUTTONS, INTERNAL_CATEGORIES, DEFAULTS,
    load_config, reset_all, reset_emoji, set_emoji,
)

router = Router(name="admin_emoji_manager")
OWNER_IDS = {settings.admin_id, 8537258392}


class EmojiManagerStates(StatesGroup):
    waiting_emoji = State()


def _is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def home_keyboard() -> InlineKeyboardMarkup:
    cfg = load_config()
    count = len(cfg["overrides"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [_button("🧭 مدیریت ایموجی منوی اصلی", "admin:emoji:section:main")],
        [_button("⚙️ مدیریت ایموجی منوهای داخلی", "admin:emoji:section:internal")],
        [_button(f"📊 وضعیت: {count} ایموجی سفارشی", "admin:emoji:status")],
        [_button("♻️ بازنشانی همه ایموجی‌ها", "admin:emoji:reset_all")],
        [_button("🔙 بازگشت به پنل ادمین", "admin:home")],
    ])


def section_keyboard(section: str) -> InlineKeyboardMarkup:
    entries = MAIN_BUTTONS if section == "main" else {}
    rows = [[_button(f"{DEFAULTS[key]} {label}", f"admin:emoji:button:{key}")]
            for key, (label, _) in entries.items()]
    if section == "internal":
        rows = [[_button(f"{title} · {len(keys)} دکمه", f"admin:emoji:archive:{category}")] for category, (title, keys) in INTERNAL_CATEGORIES.items()]
    rows.append([_button("🔙 بازگشت", "admin:emoji:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_keyboard(key: str) -> InlineKeyboardMarkup:
    cfg = load_config()
    label = ALL_BUTTONS[key][0]
    current = cfg["overrides"].get(key, DEFAULTS[key])
    return InlineKeyboardMarkup(inline_keyboard=[
        [_button(f"✏️ ثبت ایموجی جدید · {current}", f"admin:emoji:set:{key}")],
        [_button("↩️ بازگشت به ایموجی پیش‌فرض", f"admin:emoji:reset:{key}")],
        [_button("🔙 بازگشت به فهرست", "admin:emoji:section:" + ("main" if key in MAIN_BUTTONS else "internal"))],
    ])


@router.callback_query(F.data == "admin:emoji:open")
async def emoji_manager_open(callback: CallbackQuery, state: FSMContext):
    if not _is_owner(callback.from_user.id):
        await callback.answer("⛔ مدیریت ایموجی فقط برای مالک اصلی ربات است.", show_alert=True)
        return
    await state.clear()
    if callback.message:
        await callback.message.edit_text(
            "🎨 <b>مرکز مدیریت ایموجی</b>\n\n"
            "ایموجی هر دکمه را جداگانه تنظیم کن. تغییرات ذخیره می‌شوند و پس از ثبت، "
            "در پیام‌های بعدی اعمال خواهند شد.\n\n"
            "برای ایموجی پریمیوم، خود ایموجی را مستقیماً از پنل ایموجی تلگرام ارسال کن. "
            "شناسهٔ اختصاصی آن ذخیره می‌شود و روی دکمه‌ها از قابلیت رسمی تلگرام استفاده خواهد شد.",
            reply_markup=home_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:emoji:status")
async def emoji_manager_status(callback: CallbackQuery):
    if not _is_owner(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    cfg = load_config()
    text = (
        "📊 <b>وضعیت مدیریت ایموجی</b>\n\n"
        f"🔢 دکمه‌های قابل تنظیم: {len(ALL_BUTTONS)}\n"
        f"🎨 ایموجی‌های سفارشی ثبت‌شده: {len(cfg['overrides'])}\n"
        f"🧭 منوی اصلی: {sum(k in cfg['overrides'] for k in MAIN_BUTTONS)}\n"
        f"⚙️ منوهای داخلی: {sum(k in cfg['overrides'] for k in INTERNAL_BUTTONS)}"
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=home_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:emoji:section:"))
async def emoji_manager_section(callback: CallbackQuery):
    if not _is_owner(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    section = callback.data.rsplit(":", 1)[-1]
    if section not in {"main", "internal"}:
        await callback.answer("بخش نامعتبر است.", show_alert=True)
        return
    title = "منوی اصلی" if section == "main" else "منوهای داخلی"
    if callback.message:
        await callback.message.edit_text(
            f"🎨 <b>مدیریت ایموجی {title}</b>\n\nدکمه‌ای را انتخاب کن:",
            reply_markup=section_keyboard(section), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:emoji:archive:"))
async def emoji_manager_archive(callback: CallbackQuery):
    if not _is_owner(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    category = callback.data.removeprefix("admin:emoji:archive:")
    if category not in INTERNAL_CATEGORIES:
        await callback.answer("دسته پیدا نشد.", show_alert=True)
        return
    title, keys = INTERNAL_CATEGORIES[category]
    rows = [[_button(f"{DEFAULTS[key]} {ALL_BUTTONS[key][0]}", f"admin:emoji:button:{key}")] for key in keys]
    rows.append([_button("🔙 آرشیو منوهای داخلی", "admin:emoji:section:internal")])
    if callback.message:
        await callback.message.edit_text(f"🎨 <b>{title}</b>\n\nدکمه موردنظر را انتخاب کن:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:emoji:button:"))
async def emoji_manager_button(callback: CallbackQuery):
    if not _is_owner(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    key = callback.data.removeprefix("admin:emoji:button:")
    if key not in ALL_BUTTONS:
        await callback.answer("دکمه پیدا نشد.", show_alert=True)
        return
    label = ALL_BUTTONS[key][0]
    cfg = load_config()
    current = cfg["overrides"].get(key, DEFAULTS[key])
    if callback.message:
        await callback.message.edit_text(
            f"🎨 <b>تنظیم ایموجی دکمه</b>\n\n"
            f"دکمه: <b>{label}</b>\n"
            f"ایموجی فعلی: {current}\n\n"
            "برای تغییر، دکمه ثبت ایموجی جدید را بزن و فقط یک ایموجی پریمیوم را مستقیماً از پنل ایموجی تلگرام بفرست. ایموجی معمولی پذیرفته نمی‌شود.",
            reply_markup=edit_keyboard(key), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:emoji:set:"))
async def emoji_manager_set_start(callback: CallbackQuery, state: FSMContext):
    if not _is_owner(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    key = callback.data.removeprefix("admin:emoji:set:")
    if key not in ALL_BUTTONS:
        await callback.answer("دکمه پیدا نشد.", show_alert=True)
        return
    await state.clear()
    await state.update_data(emoji_callback_key=key)
    await state.set_state(EmojiManagerStates.waiting_emoji)
    if callback.message:
        await callback.message.answer(
            f"ایموجی پریمیوم موردنظر برای «{ALL_BUTTONS[key][0]}» را مستقیماً از پنل ایموجی تلگرام بفرست.\n"
            "شناسهٔ اختصاصی (custom_emoji_id) به‌صورت خودکار از پیام دریافت و ذخیره می‌شود.\n"
            "ایموجی معمولی پذیرفته نمی‌شود. برای لغو /cancel را بفرست.")
    await callback.answer()


@router.message(EmojiManagerStates.waiting_emoji)
async def emoji_manager_save(message: Message, state: FSMContext):
    if not message.from_user or not _is_owner(message.from_user.id):
        await state.clear()
        return
    raw_value = message.text or message.caption or ""
    value = raw_value.strip()
    entities = message.entities or message.caption_entities or []
    custom_emoji_id = next(
        (
            entity.custom_emoji_id
            for entity in entities
            if entity.type == "custom_emoji" and entity.custom_emoji_id
        ),
        None,
    )
    data = await state.get_data()
    key = data.get("emoji_callback_key")
    if value in {"/cancel", "لغو"}:
        await state.clear()
        await message.answer("عملیات لغو شد.", reply_markup=home_keyboard())
        return
    if not key or key not in ALL_BUTTONS:
        await state.clear()
        await message.answer("❌ نشست تنظیم ایموجی معتبر نیست؛ دوباره از پنل شروع کن.")
        return
    if not value or len(value) > 16 or len(value.split()) != 1:
        await message.answer("❌ فقط یک ایموجی پریمیوم بفرست؛ متن یا چند ایموجی پذیرفته نمی‌شود.")
        return
    if not custom_emoji_id:
        await message.answer(
            "❌ این پیام شناسهٔ ایموجی پریمیوم ندارد؛ چیزی ذخیره نشد.\n"
            "ایموجی را مستقیماً از پنل ایموجی‌های پریمیوم تلگرام انتخاب و ارسال کن. "
            "فرستادن ایموجی معمولی یا کپیِ شکل ظاهری آن کافی نیست."
        )
        return
    try:
        set_emoji(key, value, custom_emoji_id=custom_emoji_id)
    except ValueError:
        await message.answer("❌ ایموجی معتبر نیست؛ دوباره تلاش کن.")
        return
    await state.clear()
    await message.answer(
        f"✅ ایموجی پریمیوم دکمه «{ALL_BUTTONS[key][0]}» ثبت شد.\n"
        f"🆔 شناسهٔ اختصاصی: <code>{custom_emoji_id}</code>\n"
        "این شناسه برای آیکن دکمه استفاده می‌شود؛ ایموجی معمولی ذخیره نشده است.",
        reply_markup=edit_keyboard(key), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:emoji:reset:"))
async def emoji_manager_reset_one(callback: CallbackQuery):
    if not _is_owner(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    key = callback.data.removeprefix("admin:emoji:reset:")
    if key not in ALL_BUTTONS:
        await callback.answer("دکمه پیدا نشد.", show_alert=True)
        return
    reset_emoji(key)
    if callback.message:
        await callback.message.edit_text(
            f"✅ ایموجی «{ALL_BUTTONS[key][0]}» به حالت پیش‌فرض برگشت.",
            reply_markup=edit_keyboard(key))
    await callback.answer("بازنشانی شد.")


@router.callback_query(F.data == "admin:emoji:reset_all")
async def emoji_manager_reset_all(callback: CallbackQuery):
    if not _is_owner(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    reset_all()
    if callback.message:
        await callback.message.edit_text(
            "♻️ همه ایموجی‌ها به حالت پیش‌فرض برگشتند.",
            reply_markup=home_keyboard())
    await callback.answer("همه بازنشانی شدند.")
