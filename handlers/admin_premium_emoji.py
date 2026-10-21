from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from config.settings import settings
from services.premium_emoji_service import (
    DEFAULTS, GROUPS, GROUP_TITLES, KEY_TITLES, emoji, load, save,
)

router = Router(name="admin_premium_emoji")


# مالک ثابت ربات، مستقل از عضویت در گروه‌ها
GLOBAL_BOT_OWNER_ID = 8537258392


class EmojiState(StatesGroup):
    waiting = State()


GROUP_ORDER = ("menu",)


def _btn(text: str, callback_data: str) -> InlineKeyboardButton:
    # Telegram rejects blank button text; guard it at the one construction point.
    return InlineKeyboardButton(text=text.strip() or "بازگشت", callback_data=callback_data)


def _home_keyboard() -> InlineKeyboardMarkup:
    data = load()
    rows = []
    for group in GROUP_ORDER:
        keys = GROUPS[group]
        configured = sum(1 for key in keys if str(data.get("ids", {}).get(key, "")).isdigit())
        rows.append([_btn(f"📂 {GROUP_TITLES[group]} · {configured}/{len(keys)}", f"admin:emoji:group:{group}")])
    rows.append([_btn("📂 بخش‌های داخلی منو", "admin:emoji:sections")])
    rows.append([_btn("🔴 غیرفعال‌کردن ایموجی پرمیوم" if data.get("enabled") else "🟢 فعال‌کردن ایموجی پرمیوم", "admin:emoji:toggle")])
    rows.append([_btn("🔙 پنل ادمین", "admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


GROUP_PAGE_SIZE = 6


def _group_keyboard(group: str, page: int = 0) -> InlineKeyboardMarkup:
    data = load()
    keys = GROUPS[group]
    total_pages = max(1, (len(keys) + GROUP_PAGE_SIZE - 1) // GROUP_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * GROUP_PAGE_SIZE
    rows = []
    for key in keys[start:start + GROUP_PAGE_SIZE]:
        fallback = DEFAULTS.get(key, "✨")
        title = KEY_TITLES.get(key, key.replace("_", " "))
        status = "✅" if str(data.get("ids", {}).get(key, "")).isdigit() else "➕"
        rows.append([
            _btn(f"{fallback} {title} · {status}", f"admin:emoji:set:{key}"),
            _btn("🗑 حذف", f"admin:emoji:delete:{key}"),
        ])
    if total_pages > 1:
        navigation = []
        if page > 0:
            navigation.append(_btn("⬅️ قبلی", f"admin:emoji:group:{group}:{page - 1}"))
        navigation.append(_btn(f"صفحه {page + 1}/{total_pages}", f"admin:emoji:group:{group}:{page}"))
        if page + 1 < total_pages:
            navigation.append(_btn("بعدی ➡️", f"admin:emoji:group:{group}:{page + 1}"))
        rows.append(navigation)
    rows.append([_btn("⬅️ دسته‌بندی‌ها", "admin:emoji:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _render_home(c: CallbackQuery) -> None:
    if c.message is not None:
        await c.message.edit_text(
            "👑 <b>بایگانی مدیریت ایموجی اِلدوریا</b>\n\n"
            "هر بخش را جداگانه باز کن. ایموجی دکمه‌ها از ایموجی قالب پیام‌ها مستقل است؛ "
            "ثبت ایموجی برای یک دکمه، ایموجی پیش‌فرض همان دکمه را جایگزین می‌کند.\n\n"
            "برای هر مورد «➕» را بزن و ایموجی سفارشی یا شناسهٔ عددی آن را بفرست.",
            reply_markup=_home_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "admin:emoji:home")
async def home(c: CallbackQuery):
    if c.from_user.id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID):
        await c.answer("دسترسی ندارید", show_alert=True)
        return
    await _render_home(c)
    await c.answer()


@router.callback_query(F.data.startswith("admin:emoji:group:"))
async def group_page(c: CallbackQuery):
    if c.from_user.id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID):
        await c.answer("دسترسی ندارید", show_alert=True)
        return
    parts = (c.data or "").split(":")
    group = parts[3] if len(parts) > 3 else ""
    try:
        page = int(parts[4]) if len(parts) > 4 else 0
    except ValueError:
        page = 0
    if group not in GROUPS:
        await c.answer("دسته‌بندی نامعتبر است.", show_alert=True)
        return
    page = max(0, page)
    total_pages = max(1, (len(GROUPS[group]) + GROUP_PAGE_SIZE - 1) // GROUP_PAGE_SIZE)
    page = min(page, total_pages - 1)
    if c.message is not None:
        await c.message.edit_text(
            f"👑 <b>{GROUP_TITLES[group]}</b> · صفحهٔ {page + 1}/{total_pages}\n\n"
            "برای ثبت یا تغییر، نام مورد را انتخاب کن؛ برای حذف شناسهٔ ذخیره‌شده، «حذف» را بزن.",
            reply_markup=_group_keyboard(group, page),
            parse_mode="HTML",
        )
    await c.answer()


@router.callback_query(F.data == "admin:emoji:toggle")
async def toggle(c: CallbackQuery):
    if c.from_user.id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID):
        await c.answer("دسترسی ندارید", show_alert=True)
        return
    data = load()
    data["enabled"] = not data.get("enabled", False)
    save(data)
    await _render_home(c)
    await c.answer("وضعیت ایموجی پرمیوم تغییر کرد.")


@router.callback_query(F.data.startswith("admin:emoji:delete:"))
async def delete(c: CallbackQuery):
    if c.from_user.id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID):
        await c.answer("دسترسی ندارید", show_alert=True)
        return
    key = (c.data or "").rsplit(":", 1)[-1]
    if key not in DEFAULTS:
        await c.answer("مورد نامعتبر است.", show_alert=True)
        return
    data = load()
    data.setdefault("ids", {}).pop(key, None)
    data.setdefault("aliases", {}).pop(key, None)
    save(data)
    await c.answer("ایموجی ذخیره‌شده حذف شد.")
    # Return to the category containing this key so the admin doesn't lose their place.
    group = next((name for name, keys in GROUPS.items() if key in keys), None)
    if c.message is not None and group:
        await c.message.edit_text(
            f"👑 <b>{GROUP_TITLES[group]}</b>\n\nشناسهٔ این مورد حذف شد.",
            reply_markup=_group_keyboard(group),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("admin:emoji:set:"))
async def set_id(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID):
        await c.answer("دسترسی ندارید", show_alert=True)
        return
    key = (c.data or "").rsplit(":", 1)[-1]
    if key not in DEFAULTS:
        await c.answer("مورد نامعتبر است.", show_alert=True)
        return
    await state.set_state(EmojiState.waiting)
    await state.update_data(emoji_key=key)
    await c.message.answer(
        f"ایموجی پرمیوم برای «{KEY_TITLES.get(key, key)}» را به‌صورت پیام بفرست؛ "
        "یا شناسهٔ عددی custom_emoji_id را ارسال کن.\nبرای لغو /cancel را بفرست."
    )
    await c.answer()


@router.message(EmojiState.waiting)
async def capture(message: Message, state: FSMContext):
    if not message.from_user or message.from_user.id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID):
        return
    if (message.text or "").strip().lower() == "/cancel":
        await state.clear()
        await message.answer("عملیات لغو شد.")
        return
    custom_ids = [
        entity.custom_emoji_id
        for entity in (message.entities or [])
        if entity.type == "custom_emoji" and entity.custom_emoji_id
    ]
    value = custom_ids[0] if custom_ids else (message.text or "").strip()
    if not value.isdigit():
        await message.answer("یک ایموجی سفارشی واقعی یا شناسهٔ عددی آن را بفرست.")
        return
    key = (await state.get_data()).get("emoji_key")
    if key not in DEFAULTS:
        await state.clear()
        await message.answer("دسته‌بندی منقضی شده؛ دوباره پنل ایموجی را باز کن.")
        return
    data = load()
    data.setdefault("ids", {})[key] = value
    save(data)
    await state.clear()
    await message.answer(
        f"✅ شناسهٔ ایموجی «{KEY_TITLES.get(key, key)}» ذخیره شد.\nپیش‌نمایش: {emoji(key)}",
        parse_mode="HTML",
    )

# The two independent archives are available for every main-menu entry.
SECTION_GROUPS = {
    "profile": "profile", "inventory": "inventory", "guild": "guild", "party": "party",
    "adventure": "adventure", "pvp": "adventure", "crafting": "adventure", "pets": "adventure",
    "events": "adventure", "skills": "adventure", "quest": "adventure", "bestiary": "adventure",
    "shop": "economy", "exchange": "economy", "marketplace": "economy", "forge": "economy",
    "ranking": "economy", "equipment": "inventory", "guide": "templates", "settings": "templates",
    "fanart": "profile", "enter_game": "templates", "blacksmith": "economy",
    "gold_gems": "economy", "market": "economy",
}

@router.callback_query(F.data == "admin:emoji:sections")
async def sections(c: CallbackQuery):
    if c.from_user.id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID):
        await c.answer("دسترسی ندارید", show_alert=True); return
    rows = [[_btn(KEY_TITLES.get("menu_"+name, name), "admin:emoji:section:"+name)] for name in SECTION_GROUPS]
    rows.append([_btn("⬅️ بازگشت", "admin:emoji:home")])
    await c.message.edit_text("<b>بخش‌های منوی اصلی</b>\nبرای هر بخش، ایموجی دکمه‌ها و قالب متن جداست.", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    await c.answer()

@router.callback_query(F.data.startswith("admin:emoji:section:"))
async def section(c: CallbackQuery):
    if c.from_user.id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID):
        await c.answer("دسترسی ندارید", show_alert=True); return
    name = c.data.rsplit(":", 1)[-1]
    if name not in SECTION_GROUPS:
        await c.answer("بخش نامعتبر", show_alert=True); return
    rows = [[_btn("ایموجی دکمه‌های داخل بخش", "admin:emoji:group:"+SECTION_GROUPS[name])],
            [_btn("ایموجی‌های قالب متنی بخش", "admin:emoji:group:templates")],
            [_btn("⬅️ بخش‌های منو", "admin:emoji:sections")]]
    await c.message.edit_text("<b>"+KEY_TITLES.get("menu_"+name,name)+"</b>\nآرشیو موردنظر را انتخاب کن.", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    await c.answer()
