"""Premium Telegram emoji registry, text conversion, and safe keyboard icons."""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any, Callable

PATH = Path(__file__).resolve().parent.parent / "data" / "premium_emojis.json"

# Each key has one distinct ordinary emoji fallback. Keep keys stable: saved IDs use them.
DEFAULTS: dict[str, str] = {
    "gold": "💰", "gems": "💎", "boss": "🐉", "dungeon": "🗝️",
    "pet": "🐺", "pvp": "⚔️", "health": "❤️", "mana": "🔮",
    "potion": "🧪", "shop": "🏪", "rank": "🏆", "xp": "✨",
    "title": "👑", "equipment": "🛡️", "scroll": "📜", "material": "🗃️",
    "menu_profile": "👤", "menu_inventory": "🎒", "menu_skills": "🪄",
    "menu_equipment": "🪖", "menu_quest": "🧭", "menu_adventure": "🏕️",
    "menu_pvp": "🥊", "menu_crafting": "⚒️", "menu_pets": "🦊",
    "menu_events": "🎪", "menu_party": "🎉", "menu_guild": "🏰",
    "menu_ranking": "🥇", "menu_forge": "🔨", "menu_marketplace": "🛒",
    "menu_bestiary": "📖", "menu_exchange": "🔁", "menu_guide": "🗺️",
    "menu_shop": "🛍️", "menu_settings": "⚙️", "menu_fanart": "🎨",
    "menu_enter_game": "🚪", "profile_stats": "📊", "profile_fanart_select": "🖼️",
    "profile_inventory": "🎒", "profile_equipment": "🛡️", "profile_skills": "⚔️",
    "profile_titles": "🎖️", "profile_back": "🔙",
    "profile_hp_recovery": "💖", "profile_mana_recovery": "🌌",
    "guild_members": "🤝", "guild_missions": "🎯", "guild_vault": "🏦",
    "guild_buy_adventure_items": "📦", "party_members": "🧑‍🤝‍🧑",
    "menu_blacksmith": "🧰", "menu_gold_gems": "💱", "menu_market": "🏷️",
}
# Human-readable categories used by the admin archive.
GROUPS: dict[str, tuple[str, ...]] = {
    "menu": ("menu_profile", "menu_inventory", "menu_skills", "menu_equipment", "menu_quest",
             "menu_adventure", "menu_pvp", "menu_crafting", "menu_pets", "menu_events",
             "menu_party", "menu_guild", "menu_ranking", "menu_forge", "menu_marketplace",
             "menu_bestiary", "menu_exchange", "menu_guide", "menu_shop", "menu_settings",
             "menu_fanart", "menu_enter_game", "menu_blacksmith", "menu_gold_gems", "menu_market"),
    "profile": ("profile_inventory", "profile_equipment", "profile_skills", "profile_stats", "profile_hp_recovery", "profile_mana_recovery", "profile_titles", "profile_fanart_select", "profile_back"),
    "inventory": ("menu_inventory", "menu_equipment", "equipment", "potion", "health", "mana", "scroll", "material"),
    "guild": ("menu_guild", "guild_members", "guild_missions", "guild_vault", "guild_buy_adventure_items"),
    "party": ("menu_party", "party_members"),
    "adventure": ("menu_adventure", "menu_quest", "menu_pvp", "menu_crafting", "menu_pets", "menu_events", "boss", "dungeon", "pvp"),
    "economy": ("menu_shop", "menu_exchange", "menu_marketplace", "menu_forge", "menu_ranking", "gold", "gems", "shop", "rank", "xp"),
    "templates": ("gold", "gems", "boss", "dungeon", "pet", "pvp", "health", "mana", "potion", "shop", "rank", "xp", "title", "equipment", "scroll", "material"),
}
GROUP_TITLES = {
    "menu": "منوهای اصلی", "profile": "پروفایل", "inventory": "صندوقچه و تجهیزات",
    "guild": "گیلد", "party": "پارتی", "adventure": "ماجراجویی و نبرد",
    "economy": "اقتصاد و فروشگاه", "templates": "ایموجی‌های قالب پیام",
}
KEY_TITLES = {
    "gold":"طلا", "gems":"جم", "boss":"باس", "dungeon":"دانجن", "pet":"همراه",
    "pvp":"نبرد", "health":"سلامت", "mana":"مانا", "potion":"معجون", "shop":"فروشگاه",
    "rank":"رتبه", "xp":"تجربه", "title":"عنوان", "equipment":"تجهیزات", "scroll":"اسکرول",
    "material":"مواد اولیه", "menu_profile":"دکمه پروفایل", "menu_inventory":"دکمه صندوقچه",
    "menu_skills":"دکمه مهارت‌ها", "menu_equipment":"دکمه تجهیزات", "menu_quest":"دکمه مأموریت‌ها",
    "menu_adventure":"دکمه ماجراجویی", "menu_pvp":"دکمه PvP", "menu_crafting":"دکمه ساخت‌وساز",
    "menu_pets":"دکمه همراهان", "menu_events":"دکمه رویدادها", "menu_party":"دکمه پارتی",
    "menu_guild":"دکمه گیلد", "menu_ranking":"دکمه رتبه‌بندی", "menu_forge":"دکمه آهنگری",
    "menu_marketplace":"دکمه بازار بازیکنان", "menu_bestiary":"دکمه دانشنامه هیولاها",
    "menu_exchange":"دکمه تبدیل طلا و جم", "menu_guide":"دکمه راهنما", "menu_shop":"دکمه فروشگاه",
    "menu_settings":"دکمه تنظیمات", "menu_fanart":"دکمه فن‌آرت", "menu_enter_game":"دکمه ورود به بازی",
    "profile_stats":"دکمه آمار در پروفایل", "profile_fanart_select":"دکمه انتخاب فن‌آرت در پروفایل",
    "profile_inventory":"دکمه صندوقچه داخل پروفایل", "profile_equipment":"دکمه تجهیزات داخل پروفایل",
    "profile_skills":"دکمه مهارت‌ها داخل پروفایل", "profile_titles":"دکمه لقب‌ها داخل پروفایل",
    "profile_back":"دکمه بازگشت داخل پروفایل", "profile_hp_recovery":"بازیابی سلامت",
    "profile_mana_recovery":"بازیابی مانا", "guild_members":"اعضای گیلد", "guild_missions":"مأموریت‌های گیلد",
    "guild_vault":"خزانه گیلد", "guild_buy_adventure_items":"خرید آیتم‌های ماجراجویی",
    "party_members":"اعضای پارتی", "menu_blacksmith":"دکمه آهنگر", "menu_gold_gems":"دکمه تبدیل طلا و جم",
    "menu_market":"دکمه بازار",
}

def load() -> dict[str, Any]:
    if not PATH.exists():
        return {"enabled": False, "ids": {}, "catalog": {}, "aliases": {}}
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"enabled": False, "ids": {}, "catalog": {}, "aliases": {}}
    if not isinstance(data, dict):
        return {"enabled": False, "ids": {}, "catalog": {}, "aliases": {}}
    data.setdefault("enabled", False)
    data.setdefault("ids", {})
    data.setdefault("catalog", {})
    data.setdefault("aliases", {})
    return data

def save(data: dict[str, Any]) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _canonical_emoji(value: str) -> str:
    return value.replace("\ufe0f", "").replace("\ufe0e", "")

def extract_emojis(text: str) -> list[str]:
    """Extract common emoji sequences without splitting flags, keycaps or ZWJ glyphs."""
    out: list[str] = []
    i = 0
    while i < len(text):
        cp = ord(text[i])
        keycap_start = text[i] in "#*0123456789"
        is_keycap = keycap_start and i + 1 < len(text) and (
            ord(text[i + 1]) == 0x20E3 or
            (ord(text[i + 1]) == 0xFE0F and i + 2 < len(text) and ord(text[i + 2]) == 0x20E3)
        )
        is_emoji = (0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0x1F1E6 <= cp <= 0x1F1FF or is_keycap)
        if not is_emoji:
            i += 1
            continue
        start = i
        i += 1
        if is_keycap:
            if i < len(text) and ord(text[i]) == 0xFE0F:
                i += 1
            if i < len(text) and ord(text[i]) == 0x20E3:
                i += 1
            out.append(text[start:i])
            continue
        if 0x1F1E6 <= cp <= 0x1F1FF and i < len(text) and 0x1F1E6 <= ord(text[i]) <= 0x1F1FF:
            i += 1
        while i < len(text):
            c = ord(text[i])
            if c in (0xFE0E, 0xFE0F) or 0x1F3FB <= c <= 0x1F3FF:
                i += 1
            elif c == 0x20E3:
                i += 1
            elif c == 0x200D and i + 1 < len(text):
                i += 2
                while i < len(text) and (ord(text[i]) in (0xFE0E, 0xFE0F) or 0x1F3FB <= ord(text[i]) <= 0x1F3FF):
                    i += 1
            else:
                break
        out.append(text[start:i])
    return out

def register_emojis(text: str) -> None:
    data = load()
    catalog = data.setdefault("catalog", {})
    for glyph in extract_emojis(text):
        canonical = _canonical_emoji(glyph)
        if any(_canonical_emoji(str(v)) == canonical for v in catalog.values()):
            continue
        if any(_canonical_emoji(v) == canonical for v in DEFAULTS.values()):
            continue
        key = _key_for_emoji(glyph)
        catalog[key] = glyph
    save(data)

def _key_for_emoji(glyph: str) -> str:
    canonical = _canonical_emoji(glyph)
    for key, value in DEFAULTS.items():
        if _canonical_emoji(value) == canonical:
            return key
    return "custom_" + "_".join(f"{ord(ch):x}" for ch in canonical)

def catalog() -> dict[str, str]:
    result = dict(DEFAULTS)
    for key, glyph in load().get("catalog", {}).items():
        if key not in result and glyph and not any(_canonical_emoji(glyph) == _canonical_emoji(v) for v in result.values()):
            result[str(key)] = str(glyph)
    return result

def catalog_items(data: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    data = data or load()
    values = dict(DEFAULTS)
    values.update({str(k): str(v) for k, v in data.get("catalog", {}).items() if v})
    seen: set[str] = set()
    result = []
    for key, glyph in values.items():
        canonical = _canonical_emoji(glyph)
        if canonical not in seen:
            seen.add(canonical)
            result.append((key, glyph))
    return result

def _replace_known_emoji(text: str, glyph: str, emoji_id: str) -> str:
    # Avoid wrapping glyphs already inside a tg-emoji tag.
    pattern = re.compile(re.escape(glyph))
    tag_pattern = re.compile(r"<tg-emoji\b[^>]*>.*?</tg-emoji>", re.DOTALL)
    parts = []
    last = 0
    for match in tag_pattern.finditer(text):
        parts.append(pattern.sub(lambda _: f'<tg-emoji emoji-id="{escape(emoji_id)}">{glyph}</tg-emoji>', text[last:match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(pattern.sub(lambda _: f'<tg-emoji emoji-id="{escape(emoji_id)}">{glyph}</tg-emoji>', text[last:]))
    return "".join(parts)

def transform_text(text: str, data: dict[str, Any] | None = None) -> str:
    data = data or load()
    if not data.get("enabled"):
        return text
    ids = data.get("ids", {})
    aliases = data.get("aliases", {})
    for key, emoji_id in ids.items():
        emoji_id = str(emoji_id)
        if not emoji_id.isdigit():
            continue
        glyphs = [DEFAULTS.get(key), data.get("catalog", {}).get(key), *aliases.get(key, [])]
        for glyph in filter(None, glyphs):
            text = _replace_known_emoji(text, str(glyph), emoji_id)
    return text

def _text_key(text: str) -> str | None:
    low = text.lower()
    hints = {
        "رتبه": "rank", "رنک": "rank", "طلا": "gold", "گلد": "gold", "جم": "gems",
        "الماس": "gems", "باس": "boss", "دانجن": "dungeon", "سیاهچال": "dungeon",
        "پروفایل": "menu_profile", "صندوقچه": "menu_inventory", "مهارت": "menu_skills",
        "تجهیزات": "menu_equipment", "ماجراجویی": "menu_adventure", "پارتی": "menu_party",
        "گیلد": "menu_guild", "آهنگری": "menu_forge", "فروشگاه": "menu_shop",
        "راهنما": "menu_guide", "تنظیمات": "menu_settings", "فن‌آرت": "menu_fanart",
    }
    return next((key for hint, key in hints.items() if hint in low), None)

def apply_keyboard_icons(markup: Any, data: dict[str, Any] | None = None,
                         category_resolver: Callable[[str | None, str], str | None] | None = None) -> Any:
    """Set Telegram's custom emoji button icon; never empty an inline button label."""
    data = data or load()
    if not data.get("enabled"):
        return markup
    ids = data.get("ids", {})
    rows = getattr(markup, "inline_keyboard", None)
    if rows is not None:
        for row_index, row in enumerate(list(rows)):
            for index, button in enumerate(list(row)):
                text = str(getattr(button, "text", "") or "")
                if not text.strip():
                    continue
                callback_data = getattr(button, "callback_data", None)
                key = category_resolver(callback_data, text) if category_resolver else None
                if not key and callback_data:
                    callback_key = str(callback_data).lower().split(":")[-1]
                    if callback_key in DEFAULTS:
                        key = callback_key
                    elif callback_key in {"ranking", "leaderboard"}:
                        key = "rank"
                key = key or _text_key(text)
                if not key or not str(ids.get(key, "")).isdigit():
                    continue
                emoji_id = str(ids[key])
                # If the text contains only an emoji, preserve it: Telegram requires non-empty text.
                cleaned = re.sub(r"^[^\w\s]+\s*", "", text, count=1, flags=re.UNICODE)
                if cleaned.strip():
                    text_to_use = cleaned
                else:
                    text_to_use = text
                try:
                    updated = button.model_copy(update={"icon_custom_emoji_id": emoji_id, "text": text_to_use})
                    row[index] = updated
                except Exception:
                    try:
                        button.icon_custom_emoji_id = emoji_id
                        button.text = text_to_use
                    except Exception:
                        pass
        try:
            markup.inline_keyboard = rows
        except Exception:
            pass
    # Reply-keyboard labels must remain byte-for-byte unchanged for text handlers,
    # but Telegram may still display a custom icon where supported.
    reply_rows = getattr(markup, "keyboard", None)
    if reply_rows is not None:
        for row in reply_rows:
            for button in row:
                text = str(getattr(button, "text", "") or "")
                key = _text_key(text)
                if key and str(ids.get(key, "")).isdigit():
                    try:
                        button.icon_custom_emoji_id = str(ids[key])
                    except Exception:
                        pass
    return markup

def emoji(key: str) -> str:
    fallback = DEFAULTS.get(key, "✨")
    data = load()
    value = str(data.get("ids", {}).get(key, ""))
    if data.get("enabled") and value.isdigit():
        return f'<tg-emoji emoji-id="{escape(value)}">{fallback}</tg-emoji>'
    return fallback
