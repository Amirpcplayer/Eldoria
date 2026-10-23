from __future__ import annotations

import hashlib

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.admin_temp import is_admin
from services import premium_emoji_service as emoji_service

router = Router(name="admin_emoji_manager")
PAGE_SIZE = 8
MAIN_CATEGORY = "main"
INTERNAL_CATEGORY = "internal"


class EmojiManagerState(StatesGroup):
    waiting_custom_emoji = State()
    waiting_search = State()


def _data() -> dict:
    return emoji_service.load()


def _title(key: str, data: dict | None = None) -> str:
    title = getattr(emoji_service, "KEY_TITLES", {}).get(key)
    if title:
        return title
    data = data or _data()
    catalog_glyph = data.get("catalog", {}).get(key, "")
    if key.startswith("menu_"):
        return f"دکمهٔ {key.removeprefix('menu_').replace('_', ' ')}"
    if key.startswith("profile_"):
        return f"پروفایل · {key.removeprefix('profile_').replace('_', ' ')}"
    if key.startswith("custom_") and catalog_glyph:
        return f"ایموجی ثبت‌شدهٔ {catalog_glyph}"
    return key.replace("_", " ").strip().capitalize()


def _glyph(key: str, data: dict | None = None) -> str:
    data = data or _data()
    return (
        emoji_service.DEFAULTS.get(key)
        or data.get("catalog", {}).get(key)
        or "✨"
    )


def _all_keys(data: dict | None = None) -> list[str]:
    """Include every built-in, catalog, saved-ID and legacy key in the manager."""
    data = data or _data()
    keys = set(emoji_service.DEFAULTS)
    keys.update(str(key) for key in data.get("catalog", {}))
    keys.update(str(key) for key in data.get("ids", {}))
    # Keep legacy aliases visible so old installations can still clean them up.
    keys.update(str(key) for key in data.get("aliases", {}))
    return sorted(keys, key=lambda key: (not key.startswith("menu_"), key.casefold()))


def _category_keys(category: str, data: dict | None = None) -> list[str]:
    keys = _all_keys(data)
    if category == MAIN_CATEGORY:
        return [key for key in keys if key.startswith("menu_")]
    if category == INTERNAL_CATEGORY:
        return [key for key in keys if not key.startswith("menu_")]
    return []


def _is_registered(key: str, data: dict) -> bool:
    return str(data.get("ids", {}).get(key, "")).isdigit()


def _key_token(key: str) -> str:
    """Compact stable callback token; Telegram callback_data is limited to 64 bytes."""
    return hashlib.blake2s(key.encode("utf-8"), digest_size=5).hexdigest()


def _key_from_token(token: str, data: dict) -> str | None:
    return next((key for key in _all_keys(data) if _key_token(key) == token), None)


def _home_keyboard(data: dict) -> InlineKeyboardMarkup:
    """The manager intentionally exposes exactly two top-level sections."""
    main_keys = _category_keys(MAIN_CATEGORY, data)
    internal_keys = _category_keys(INTERNAL_CATEGORY, data)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🏠 بخش اصلی · {len(main_keys)} ایموجی",
            callback_data="emoji:cat:main:0",
        )],
        [InlineKeyboardButton(
            text=f"🧭 بخش داخلی · {len(internal_keys)} ایموجی",
            callback_data="emoji:cat:internal:0",
        )],
        [InlineKeyboardButton(text="🔙 بازگشت به پنل ادمین", callback_data="admin:home")],
    ])


def _category_keyboard(category: str, page: int, data: dict) -> InlineKeyboardMarkup:
    keys = _category_keys(category, data)
    pages = max(1, (len(keys) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    rows = []
    for key in keys[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        status = "✅" if _is_registered(key, data) else "▫️"
        rows.append([InlineKeyboardButton(
            text=f"{_glyph(key, data)} {_title(key, data)} {status}"[:64],
            callback_data=f"emoji:key:{_key_token(key)}:{page}:{category}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"emoji:cat:{category}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="emoji:home"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton(text="بعدی ➡️", callback_data=f"emoji:cat:{category}:{page + 1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔎 جست‌وجو", callback_data="emoji:search")])
    rows.append([InlineKeyboardButton(text="🏠 مرکز مدیریت ایموجی", callback_data="emoji:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _detail_keyboard(key: str, page: int, category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 ثبت / جایگزینی Custom Emoji", callback_data=f"emoji:set:{_key_token(key)}:{page}:{category}")],
        [InlineKeyboardButton(text="♻️ حذف تنظیم و بازگشت به پیش‌فرض", callback_data=f"emoji:reset:{_key_token(key)}:{page}:{category}")],
        [InlineKeyboardButton(text="🔙 بازگشت به فهرست", callback_data=f"emoji:cat:{category}:{page}")],
        [InlineKeyboardButton(text="🏠 مرکز مدیریت ایموجی", callback_data="emoji:home")],
    ])


def _category_title(category: str) -> str:
    return "منوی اصلی" if category == MAIN_CATEGORY else "منوی داخلی"


def _valid_key(key: str, data: dict) -> bool:
    return key in emoji_service.DEFAULTS or key in data.get("catalog", {}) or key in data.get("ids", {}) or key in data.get("aliases", {})


async def _authorized(callback: CallbackQuery) -> bool:
    if is_admin(callback.from_user.id):
        return True
    await callback.answer("⛔ مدیریت ایموجی فقط برای مالک ربات فعال است.", show_alert=True)
    return False


@router.callback_query(F.data.in_({"emoji:home", "admin:emoji:home"}))
async def emoji_home(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    await state.clear()
    data = _data()
    all_keys = _all_keys(data)
    registered = sum(1 for key in all_keys if _is_registered(key, data))
    if callback.message:
        await callback.message.edit_text(
            "╭━━━ ✦ 🎨 مرکز فرماندهی ایموجی ✦ ━━━╮\n"
            "مدیریت یکپارچهٔ ظاهر World Eldoria\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"🧩 کل کلیدهای قابل مدیریت: {len(all_keys)}\n"
            f"💠 ایموجی‌های ویژهٔ ثبت‌شده: {registered}\n"
            f"⚙️ وضعیت سراسری: {'فعال' if data.get('enabled') else 'غیرفعال'}\n\n"
            "یکی از دو بخش اصلی را باز کن. هر کلید مستقل است؛ تغییر یک مورد تنظیم بقیه را دست‌کاری نمی‌کند.\n"
            "✅ ثبت‌شده · ▫️ پیش‌فرض",
            reply_markup=_home_keyboard(data),
        )
    await callback.answer()


@router.callback_query(F.data == "emoji:toggle")
async def emoji_toggle(callback: CallbackQuery):
    if not await _authorized(callback):
        return
    data = _data()
    data["enabled"] = not bool(data.get("enabled"))
    emoji_service.save(data)
    if callback.message:
        await callback.message.edit_text(
            "╭━━━ ✦ 🎨 مرکز فرماندهی ایموجی ✦ ━━━╮\n"
            "تنظیمات سراسری ذخیره شد.\n\n"
            "توجه: خاموش‌کردن این گزینه فقط نمایش Custom Emoji را غیرفعال می‌کند؛ شناسه‌های ثبت‌شده حذف نمی‌شوند.",
            reply_markup=_home_keyboard(data),
        )
    await callback.answer("وضعیت ایموجی‌های ویژه ذخیره شد.")


@router.callback_query(F.data.startswith("emoji:cat:"))
async def emoji_category(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    await state.clear()
    parts = (callback.data or "").split(":")
    category = parts[2] if len(parts) > 2 else ""
    try:
        page = max(0, int(parts[3])) if len(parts) > 3 else 0
    except ValueError:
        page = 0
    if category not in {MAIN_CATEGORY, INTERNAL_CATEGORY}:
        await callback.answer("دسته‌بندی نامعتبر است.", show_alert=True)
        return
    data = _data()
    keys = _category_keys(category, data)
    pages = max(1, (len(keys) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, pages - 1)
    if callback.message:
        await callback.message.edit_text(
            f"🎨 مدیریت ایموجی / {_category_title(category)}\n\n"
            f"کلیدها: {len(keys)} · صفحهٔ {page + 1} از {pages}\n"
            "برای مدیریت هر مورد روی همان ردیف بزن.",
            reply_markup=_category_keyboard(category, page, data),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("emoji:key:"))
async def emoji_key_detail(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    await state.clear()
    parts = (callback.data or "").split(":")
    if len(parts) < 5:
        await callback.answer("درخواست ناقص است.", show_alert=True)
        return
    data = _data()
    key = _key_from_token(parts[2], data)
    if key is None:
        await callback.answer("کلید ایموجی پیدا نشد؛ فهرست را دوباره باز کن.", show_alert=True)
        return
    try:
        page = int(parts[3])
    except ValueError:
        page = 0
    category = parts[4] if parts[4] in {MAIN_CATEGORY, INTERNAL_CATEGORY} else (
        MAIN_CATEGORY if key.startswith("menu_") else INTERNAL_CATEGORY
    )
    data = _data()
    if not _valid_key(key, data):
        await callback.answer("این کلید در فهرست ایموجی‌ها پیدا نشد.", show_alert=True)
        return
    emoji_id = str(data.get("ids", {}).get(key, ""))
    aliases = data.get("aliases", {}).get(key, [])
    alias_text = f"\n🔗 نام‌های جایگزین: {', '.join(map(str, aliases))}" if aliases else ""
    if callback.message:
        await callback.message.edit_text(
            "╭━━━ ✦ 🧩 جزئیات ایموجی ✦ ━━━╮\n"
            f"{_glyph(key, data)}  {_title(key, data)}\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"🔑 کلید پایدار: {key}\n"
            f"🎭 ایموجی پیش‌فرض: {_glyph(key, data)}\n"
            f"🆔 شناسهٔ ویژه: {emoji_id if emoji_id.isdigit() else 'ثبت نشده'}\n"
            f"📡 وضعیت: {'Custom Emoji ثبت شده' if emoji_id.isdigit() else 'استفاده از پیش‌فرض'}"
            f"{alias_text}\n\n"
            "برای ثبت یا جایگزینی، یک Custom Emoji تلگرام بفرست. شناسه از entity پیام خوانده می‌شود.",
            reply_markup=_detail_keyboard(key, page, category),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("emoji:set:"))
async def emoji_set_start(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    parts = (callback.data or "").split(":")
    if len(parts) < 5:
        await callback.answer("درخواست ناقص است.", show_alert=True)
        return
    data = _data()
    key = _key_from_token(parts[2], data)
    if key is None:
        await callback.answer("کلید ایموجی پیدا نشد؛ فهرست را دوباره باز کن.", show_alert=True)
        return
    try:
        page = max(0, int(parts[3]))
    except ValueError:
        page = 0
    category = parts[4] if parts[4] in {MAIN_CATEGORY, INTERNAL_CATEGORY} else (
        MAIN_CATEGORY if key.startswith("menu_") else INTERNAL_CATEGORY
    )
    if not _valid_key(key, data):
        await callback.answer("کلید نامعتبر است.", show_alert=True)
        return
    await state.clear()
    await state.update_data(emoji_key=key, emoji_page=page, emoji_category=category)
    await state.set_state(EmojiManagerState.waiting_custom_emoji)
    if callback.message:
        await callback.message.answer(
            f"🎨 ثبت ایموجی برای «{_title(key)}»\n\n"
            "یک Custom Emoji تلگرام را مستقیماً بفرست؛ متن یا ایموجی معمولی شناسهٔ ویژه ندارد.\n"
            "لغو عملیات: /cancel"
        )
    await callback.answer()


@router.message(EmojiManagerState.waiting_custom_emoji)
async def emoji_set_finish(message: Message, state: FSMContext):
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return
    text = message.text or message.caption or ""
    if text.strip().casefold() in {"/cancel", "لغو"}:
        await state.clear()
        await message.answer("عملیات ثبت ایموجی لغو شد.")
        return
    entities = list(message.entities or []) + list(message.caption_entities or [])
    custom = next((
        entity for entity in entities
        if getattr(entity, "type", None) == "custom_emoji"
        and str(getattr(entity, "custom_emoji_id", "")).isdigit()
    ), None)
    if custom is None:
        await message.answer(
            "❌ شناسهٔ Custom Emoji پیدا نشد. یک ایموجی ویژهٔ تلگرام را مستقیماً بفرست؛ "
            "ایموجی معمولی قابل تبدیل به شناسهٔ ویژه نیست."
        )
        return
    payload = await state.get_data()
    key = str(payload.get("emoji_key", ""))
    if not _valid_key(key, _data()):
        await state.clear()
        await message.answer("❌ کلید انتخاب‌شده دیگر در فهرست وجود ندارد؛ دوباره از /admin وارد شو.")
        return
    data = _data()
    data.setdefault("ids", {})[key] = str(custom.custom_emoji_id)
    data["enabled"] = True
    emoji_service.save(data)
    page = int(payload.get("emoji_page", 0))
    category = str(payload.get("emoji_category", INTERNAL_CATEGORY))
    await state.clear()
    await message.answer(
        f"✅ ایموجی «{_title(key)}» ذخیره شد.\n"
        f"🆔 شناسه: {custom.custom_emoji_id}\n"
        "تنظیم سایر کلیدها بدون تغییر باقی ماند.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به همین بخش", callback_data=f"emoji:cat:{category}:{page}")],
            [InlineKeyboardButton(text="🏠 مرکز مدیریت ایموجی", callback_data="emoji:home")],
        ]),
    )


@router.callback_query(F.data.startswith("emoji:reset:"))
async def emoji_reset(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    parts = (callback.data or "").split(":")
    if len(parts) < 5:
        await callback.answer("درخواست ناقص است.", show_alert=True)
        return
    data = _data()
    key = _key_from_token(parts[2], data)
    if key is None:
        await callback.answer("کلید ایموجی پیدا نشد؛ فهرست را دوباره باز کن.", show_alert=True)
        return
    try:
        page = max(0, int(parts[3]))
    except ValueError:
        page = 0
    category = parts[4] if parts[4] in {MAIN_CATEGORY, INTERNAL_CATEGORY} else (
        MAIN_CATEGORY if key.startswith("menu_") else INTERNAL_CATEGORY
    )
    if not _valid_key(key, data):
        await callback.answer("کلید نامعتبر است.", show_alert=True)
        return
    data.setdefault("ids", {}).pop(key, None)
    emoji_service.save(data)
    await state.clear()
    if callback.message:
        await callback.message.edit_text(
            f"♻️ تنظیم ویژهٔ «{_title(key)}» حذف شد؛ ایموجی پیش‌فرض فعال است.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 بازگشت به فهرست", callback_data=f"emoji:cat:{category}:{page}")],
                [InlineKeyboardButton(text="🏠 مرکز مدیریت ایموجی", callback_data="emoji:home")],
            ]),
        )
    await callback.answer("تنظیم ذخیره شد.")


@router.callback_query(F.data == "emoji:search")
async def emoji_search_start(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    await state.clear()
    await state.set_state(EmojiManagerState.waiting_search)
    if callback.message:
        await callback.message.answer(
            "🔎 نام بخش، عنوان یا کلید ایموجی را بفرست.\n"
            "نمونه: پروفایل، hp، صندوقچه، menu_guild\n"
            "لغو: /cancel"
        )
    await callback.answer()


@router.message(EmojiManagerState.waiting_search)
async def emoji_search_finish(message: Message, state: FSMContext):
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return
    query = (message.text or "").strip().casefold()
    if query in {"/cancel", "لغو"}:
        await state.clear()
        await message.answer("جست‌وجو لغو شد.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🏠 مرکز مدیریت ایموجی", callback_data="emoji:home")]]
        ))
        return
    if not query:
        await message.answer("یک نام یا کلید برای جست‌وجو بفرست.")
        return
    data = _data()
    matches = [
        key for key in _all_keys(data)
        if query in key.casefold() or query in _title(key, data).casefold() or query in _glyph(key, data).casefold()
    ][:20]
    if not matches:
        await message.answer(
            "موردی پیدا نشد. کلیدهای ثبت‌شده، پیش‌فرض و قدیمی جست‌وجو می‌شوند.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔎 جست‌وجوی دوباره", callback_data="emoji:search")],
                [InlineKeyboardButton(text="🏠 مرکز مدیریت ایموجی", callback_data="emoji:home")],
            ]),
        )
        await state.clear()
        return
    rows = []
    for key in matches:
        category = MAIN_CATEGORY if key.startswith("menu_") else INTERNAL_CATEGORY
        status = "✅" if _is_registered(key, data) else "▫️"
        rows.append([InlineKeyboardButton(
            text=f"{_glyph(key, data)} {_title(key, data)} {status}"[:64],
            callback_data=f"emoji:key:{_key_token(key)}:0:{category}",
        )])
    rows.append([InlineKeyboardButton(text="🔎 جست‌وجوی دوباره", callback_data="emoji:search")])
    rows.append([InlineKeyboardButton(text="🏠 مرکز مدیریت ایموجی", callback_data="emoji:home")])
    await state.clear()
    await message.answer(
        f"🔎 نتیجهٔ جست‌وجو برای «{query[:80]}»\n"
        f"{len(matches)} مورد اول (حداکثر ۲۰ مورد):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
