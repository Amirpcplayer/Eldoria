from __future__ import annotations

import re
from typing import Any

from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import TelegramMethod
from aiogram.types import InlineKeyboardMarkup

from services.premium_emoji_service import apply_keyboard_icons, load

# Exact callback mappings are intentionally explicit so each menu button can be
# customized independently instead of sharing a broad category accidentally.
EXACT: dict[str, str] = {
    "menu:profile": "menu_profile", "menu:inventory": "menu_inventory",
    "menu:skills": "menu_skills", "menu:equipment": "menu_equipment",
    "menu:quest": "menu_quest", "menu:adventure": "menu_adventure",
    "menu:pvp": "menu_pvp", "menu:crafting": "menu_crafting",
    "menu:pets": "menu_pets", "menu:events": "menu_events",
    "menu:party": "menu_party", "menu:guild": "menu_guild",
    "menu:ranking": "menu_ranking", "menu:forge": "menu_forge",
    "menu:marketplace": "menu_marketplace", "menu:bestiary": "menu_bestiary",
    "menu:exchange": "menu_exchange", "menu:guide": "menu_guide",
    "menu:shop": "menu_shop", "menu:settings": "menu_settings",
    "menu:fanart": "menu_fanart", "menu:enter_game": "menu_enter_game",
    "menu:blacksmith": "menu_blacksmith", "menu:gold_gems": "menu_gold_gems",
    "menu:market": "menu_market",
    "profile:stats": "profile_stats", "profile:fanart": "profile_fanart_select",
    "potion:choose:hp": "profile_hp_recovery", "potion:choose:mana": "profile_mana_recovery",
    "party:members": "party_members", "party:kick:list": "party_members",
    "guild:members": "guild_members", "guild:missions": "guild_missions",
    "guild:vault": "guild_vault", "guild:buy_adventure_items": "guild_buy_adventure_items",
}
HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("اعضای گیلد", "اعضای گیلد", "اعضا"), "guild_members"),
    (("مأموریت گیلد", "ماموریت گیلد", "ماموریت‌های گیلد"), "guild_missions"),
    (("خزانه گیلد", "خزانه"), "guild_vault"),
    (("خرید آیتم", "خرید مواد ماجراجویی"), "guild_buy_adventure_items"),
    (("پروفایل",), "menu_profile"), (("صندوقچه",), "menu_inventory"),
    (("مهارت",), "menu_skills"), (("تجهیزات",), "menu_equipment"),
    (("مأموریت", "ماموریت"), "menu_quest"), (("ماجراجویی",), "menu_adventure"),
    (("پارتی",), "menu_party"), (("گیلد",), "menu_guild"),
    (("رتبه‌بندی", "رتبه بندی"), "menu_ranking"), (("آهنگری", "آهنگر"), "menu_forge"),
    (("بازار بازیکنان", "بازار"), "menu_marketplace"), (("دانشنامه", "هیولاها"), "menu_bestiary"),
    (("تبدیل طلا", "تبدیل جم"), "menu_exchange"), (("راهنما",), "menu_guide"),
    (("فروشگاه",), "menu_shop"), (("تنظیمات",), "menu_settings"),
    (("فن‌آرت", "فن آرت"), "menu_fanart"), (("پت", "همراه"), "menu_pets"),
    (("رویداد",), "menu_events"), (("حمله", "نبرد", "مبارزه"), "menu_pvp"),
    (("باس", "غول"), "boss"), (("دانجن", "سیاهچال"), "dungeon"),
    (("طلا", "گلد"), "gold"), (("جم", "الماس"), "gems"),
    (("معجون", "اکسیر"), "potion"), (("سلامت", "درمان", "هیل"), "health"),
    (("مانا", "جادو"), "mana"), (("تجربه", "xp"), "xp"),
    (("عنوان",), "title"), (("اسکرول", "طومار"), "scroll"),
    (("مواد", "منابع"), "material"),
)

def _category(callback_data: str | None, text: str) -> str | None:
    data = (callback_data or "").lower()
    if data in EXACT:
        return EXACT[data]
    # Callback namespaces cover dynamically generated buttons such as guild action pages.
    if data.startswith("guild:") and ("mission" in data or "quest" in data):
        return "guild_missions"
    if data.startswith("guild:") and "vault" in data:
        return "guild_vault"
    if data.startswith("guild:") and ("adventure" in data or "material" in data or "buy_item" in data):
        return "guild_buy_adventure_items"
    if data.startswith("party:") and ("member" in data or "kick" in data):
        return "party_members"
    clean = re.sub(r"[\u200c\s]+", " ", text.lower())
    for hints, key in HINTS:
        if any(hint in clean for hint in hints):
            return key
    return None

class PremiumEmojiButtonsMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method: TelegramMethod[Any]) -> Any:
        markup = getattr(method, "reply_markup", None)
        if isinstance(markup, InlineKeyboardMarkup):
            data = load()
            if data.get("enabled") and data.get("ids"):
                apply_keyboard_icons(markup, data, category_resolver=_category)
                try:
                    method = method.model_copy(update={
                        "reply_markup": markup.model_copy(update={"inline_keyboard": markup.inline_keyboard})
                    })
                except Exception:
                    pass
        return await make_request(bot, method)
