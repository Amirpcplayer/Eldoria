from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.admin_temp import is_admin
from services import premium_emoji_service as emoji_service

router = Router()
PAGE_SIZE = 8


class EmojiManagerState(StatesGroup):
    waiting_custom_emoji = State()


def _data():
    return emoji_service.load()


def _title(key: str) -> str:
    return emoji_service.KEY_TITLES.get(key, key.replace("_", " ").capitalize())


def _glyph(key: str) -> str:
    return emoji_service.DEFAULTS.get(key) or emoji_service.load().get("catalog", {}).get(key, "✨")


def _categories() -> list[tuple[str, str]]:
    return [
        ("menu", "🏠 منوی اصلی"),
        ("internal", "🧭 منوی داخلی و پنل‌ها"),
        ("profile", "👤 پروفایل"),
        ("inventory", "🎒 صندوقچه و تجهیزات"),
        ("adventure", "⚔️ ماجراجویی و نبرد"),
        ("economy", "💰 اقتصاد و فروشگاه"),
        ("guild", "🏰 گیلد"),
        ("party", "👥 پارتی"),
        ("templates", "🧩 قالب پیام‌ها و آمار"),
    ]


def _category_keys(category: str, data: dict) -> list[str]:
    keys = list(emoji_service.GROUPS.get(category, ()))
    # Surface legacy and panel/action icons that are not part of the game main menu.
    if category == "internal":
        main_keys = set(emoji_service.GROUPS.get("menu", ()))
        for group_name, group_keys in emoji_service.GROUPS.items():
            if group_name not in {"menu", "templates"}:
                main_keys.update(group_keys)
        known = set(emoji_service.DEFAULTS) | set(data.get("catalog", {})) | set(data.get("ids", {}))
        keys.extend(k for k in sorted(known) if k not in main_keys and not k.startswith("menu_"))
    # Keep all saved/known template settings discoverable, including legacy keys.
    if category == "templates":
        keys.extend(k for k in data.get("ids", {}) if k not in keys and not k.startswith("menu_"))
    return list(dict.fromkeys(k for k in keys if k in emoji_service.DEFAULTS or k in data.get("catalog", {}) or k in data.get("ids", {})))


def _home_keyboard(data: dict) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"emoji:cat:{key}")]
        for key, label in _categories()
    ]
    status = "🟢 ایموجی‌های ویژه فعال" if data.get("enabled") else "⚪️ ایموجی‌های ویژه غیرفعال"
    rows.append([InlineKeyboardButton(text=status, callback_data="emoji:toggle")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت به پنل ادمین", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _category_keyboard(category: str, page: int, data: dict) -> InlineKeyboardMarkup:
    keys = _category_keys(category, data)
    pages = max(1, (len(keys) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    rows = []
    for key in keys[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        emoji_id = str(data.get("ids", {}).get(key, ""))
        status = "✅" if emoji_id.isdigit() else "▫️"
        rows.append([InlineKeyboardButton(
            text=f"{_glyph(key)}  {_title(key)}  {status}",
            callback_data=f"emoji:key:{key}:{page}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"emoji:cat:{category}:{page-1}"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton(text="بعدی ➡️", callback_data=f"emoji:cat:{category}:{page+1}"))
    if nav:
        rows.append(nav)
    rows.extend([
        [InlineKeyboardButton(text="🔎 نمایش همه کلیدها در این بخش", callback_data=f"emoji:catinfo:{category}")],
        [InlineKeyboardButton(text="↩️ دسته‌بندی‌ها", callback_data="emoji:home")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _detail_keyboard(key: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 ثبت ایموجی ویژه", callback_data=f"emoji:set:{key}:{page}")],
        [InlineKeyboardButton(text="♻️ بازگشت به ایموجی پیش‌فرض", callback_data=f"emoji:reset:{key}:{page}")],
        [InlineKeyboardButton(text="🔙 بازگشت به فهرست", callback_data=f"emoji:cat:{_category_for(key)}:{page}")],
        [InlineKeyboardButton(text="🏠 مرکز مدیریت ایموجی", callback_data="emoji:home")],
    ])


def _category_for(key: str) -> str:
    for category, keys in emoji_service.GROUPS.items():
        if key in keys:
            return category
    return "templates"


async def _authorized(callback: CallbackQuery) -> bool:
    if is_admin(callback.from_user.id):
        return True
    await callback.answer("⛔ این بخش فقط برای مالک ربات است.", show_alert=True)
    return False


@router.callback_query(F.data == "emoji:home")
async def emoji_home(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    await state.clear()
    data = _data()
    if callback.message:
        await callback.message.edit_text(
            "╭─── ✦ 🎨 ✦ ───╮\n"
            "      مرکز مدیریت ایموجی\n"
            "╰────────────────╯\n\n"
            "ایموجی‌های ویژهٔ دکمه‌ها و قالب‌های اِلدوریا را از اینجا مدیریت کن.\n"
            "✅ یعنی برای آن کلید ایموجی ویژه ثبت شده؛ ▫️ یعنی از ایموجی پیش‌فرض استفاده می‌شود.\n\n"
            f"کلیدهای ثبت‌شده: {sum(1 for v in data.get('ids', {}).values() if str(v).isdigit())}",
            reply_markup=_home_keyboard(data),
        )
    await callback.answer()


@router.callback_query(F.data == "admin:emoji:home")
async def emoji_home_from_admin(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    await state.clear()
    data = _data()
    if callback.message:
        await callback.message.edit_text(
            "╭─── ✦ 🎨 ✦ ───╮\n"
            "      مرکز مدیریت ایموجی\n"
            "╰────────────────╯\n\n"
            "ایموجی‌های ویژهٔ دکمه‌ها و قالب‌های اِلدوریا را از اینجا مدیریت کن.\n"
            "هر کلید تنظیم مستقل دارد؛ تغییر یک ایموجی، تنظیمات دیگر را پاک نمی‌کند.\n\n"
            f"کلیدهای ثبت‌شده: {sum(1 for v in data.get('ids', {}).values() if str(v).isdigit())}",
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
        await callback.message.edit_reply_markup(reply_markup=_home_keyboard(data))
    await callback.answer("تنظیمات ایموجی ذخیره شد.")


@router.callback_query(F.data.startswith("emoji:cat:"))
async def emoji_category(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    await state.clear()
    parts = (callback.data or "").split(":")
    category = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0
    if category not in {key for key, _ in _categories()}:
        await callback.answer("دسته‌بندی نامعتبر است.", show_alert=True)
        return
        await callback.message.edit_text(
            f"🎨 مدیریت ایموجی‌ها  /  {_dict_category(category)}\n\n"
            "یک کلید را انتخاب کن. علامت وضعیت نشان می‌دهد ایموجی ویژه ثبت شده یا خیر.",
            reply_markup=_category_keyboard(category, page, _data()),
        )
    await callback.answer()


def _dict_category(category: str) -> str:
    return dict(_categories()).get(category, emoji_service.GROUP_TITLES.get(category, category))


@router.callback_query(F.data.startswith("emoji:catinfo:"))
async def emoji_category_info(callback: CallbackQuery):
    if not await _authorized(callback):
        return
    category = (callback.data or "").split(":")[-1]
    data = _data()
    keys = _category_keys(category, data)
    lines = [f"{_glyph(k)}  {_title(k)}  ·  {'ثبت‌شده' if str(data.get('ids', {}).get(k, '')).isdigit() else 'پیش‌فرض'}" for k in keys]
    if callback.message:
        await callback.message.edit_text(
            f"📋 فهرست {_dict_category(category)}\n\n" + ("\n".join(lines) or "در این دسته کلیدی موجود نیست."),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"emoji:cat:{category}:0")],
                [InlineKeyboardButton(text="🏠 مرکز مدیریت ایموجی", callback_data="emoji:home")],
            ]),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("emoji:key:"))
async def emoji_key_detail(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    await state.clear()
    _, _, key, page = (callback.data or "").split(":")
    data = _data()
    if key not in emoji_service.DEFAULTS and key not in data.get("catalog", {}) and key not in data.get("ids", {}):
        await callback.answer("کلید پیدا نشد.", show_alert=True)
        return
    emoji_id = str(data.get("ids", {}).get(key, ""))
    if callback.message:
        await callback.message.edit_text(
            f"╭─── ✦ 🧩 ✦ ───╮\n"
            f"  {_glyph(key)} {_title(key)}\n"
            f"╰────────────────╯\n\n"
            f"🔑 کلید: {key}\n"
            f"🎭 ایموجی پیش‌فرض: {_glyph(key)}\n"
            f"🆔 شناسهٔ ثبت‌شده: {emoji_id if emoji_id.isdigit() else 'ثبت نشده'}\n"
            f"📡 وضعیت: {'ایموجی ویژه فعال است' if emoji_id.isdigit() else 'استفاده از حالت پیش‌فرض'}\n\n"
            "برای ثبت، روی «ثبت ایموجی ویژه» بزن و سپس یک ایموجی ویژهٔ تلگرام را در همین گفت‌وگو بفرست.",
            reply_markup=_detail_keyboard(key, int(page)),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("emoji:set:"))
async def emoji_set_start(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    _, _, key, page = (callback.data or "").split(":")
    await state.clear()
    await state.update_data(emoji_key=key, emoji_page=int(page))
    await state.set_state(EmojiManagerState.waiting_custom_emoji)
    if callback.message:
        await callback.message.answer(
            f"🎨 ثبت ایموجی برای «{_title(key)}»\n\n"
            "حالا فقط یک ایموجی ویژه (Custom Emoji) از مجموعهٔ ایموجی‌های تلگرام بفرست.\n"
            "شناسه به‌صورت خودکار از پیام استخراج و برای همین کلید ذخیره می‌شود.\n\n"
            "برای لغو، /cancel بفرست."
        )
    await callback.answer()


@router.message(EmojiManagerState.waiting_custom_emoji)
async def emoji_set_finish(message: Message, state: FSMContext):
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return
    text = message.text or message.caption or ""
    entities = list(message.entities or []) + list(message.caption_entities or [])
    custom = next((e for e in entities if getattr(e, "type", None) == "custom_emoji" and str(getattr(e, "custom_emoji_id", "")).isdigit()), None)
    if text.strip().lower() in {"/cancel", "لغو"}:
        await state.clear()
        await message.answer("عملیات ثبت ایموجی لغو شد.")
        return
    if custom is None:
        await message.answer("❌ این پیام شناسهٔ ایموجی ویژه ندارد. یک ایموجی ویژهٔ تلگرام را مستقیماً بفرست؛ متن یا ایموجی معمولی قابل تبدیل به شناسهٔ ویژه نیست.")
        return
    payload = await state.get_data()
    key = str(payload.get("emoji_key", ""))
    page = int(payload.get("emoji_page", 0))
    data = _data()
    ids = data.setdefault("ids", {})
    ids[key] = str(custom.custom_emoji_id)
    data["enabled"] = True
    emoji_service.save(data)
    await state.clear()
    await message.answer(
        f"✅ ایموجی «{_title(key)}» ذخیره شد.\n"
        f"🎭 پیش‌نمایش: {_glyph(key)}\n"
        f"🆔 شناسه: {custom.custom_emoji_id}\n\n"
        "تغییر برای پیام‌ها و دکمه‌هایی که از این کلید استفاده می‌کنند اعمال می‌شود."
    )


@router.callback_query(F.data.startswith("emoji:reset:"))
async def emoji_reset(callback: CallbackQuery, state: FSMContext):
    if not await _authorized(callback):
        return
    _, _, key, page = (callback.data or "").split(":")
    data = _data()
    data.setdefault("ids", {}).pop(key, None)
    emoji_service.save(data)
    await state.clear()
    if callback.message:
        await callback.message.edit_text(
            f"♻️ تنظیم ایموجی «{_title(key)}» حذف شد و به حالت پیش‌فرض برگشت.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 بازگشت به فهرست", callback_data=f"emoji:cat:{_category_for(key)}:{int(page)}")],
                [InlineKeyboardButton(text="🏠 مرکز مدیریت ایموجی", callback_data="emoji:home")],
            ]),
        )
    await callback.answer("ذخیره شد.")
