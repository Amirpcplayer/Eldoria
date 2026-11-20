from __future__ import annotations

import json
import os
import tempfile
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Any

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "emoji_manager.json"

# Stable callback keys make the configuration independent of button order.
MAIN_BUTTONS: dict[str, tuple[str, str]] = {
    "menu:profile": ("پروفایل", "👤"),
    "menu:inventory": ("صندوقچه", "🗃️"),
    "menu:skills": ("مهارت‌ها", "⚔️"),
    "menu:equipment": ("تجهیزات", "🛡️"),
    "menu:quest": ("مأموریت‌ها", "📜"),
    "menu:adventure": ("ماجراجویی", "🗺️"),
    "menu:crafting": ("کرفتینگ", "🔨"),
    "menu:pets": ("پت", "🐾"),
    "menu:events": ("ایونت", "🎉"),
    "menu:party": ("پارتی", "👥"),
    "menu:guild": ("گیلد", "🛡️"),
    "menu:ranking": ("رتبه‌بندی", "🏆"),
    "menu:forge": ("آهنگری", "⚒️"),
    "menu:marketplace": ("بازار بازیکنان", "🏪"),
    "menu:bestiary": ("دفترچه هیولا", "📖"),
    "menu:exchange": ("تبدیل گلد به جم", "💱"),
    "menu:guide": ("راهنما", "📖"),
    "menu:shop": ("فروشگاه", "🛒"),
    "menu:settings": ("تنظیمات", "⚙️"),
    "menu:enter_game": ("ورود به بازی", "🎮"),
}
INTERNAL_BUTTONS: dict[str, tuple[str, str]] = {
    "profile:stats": ("آمار کامل پروفایل", "📊"),
    "profile:fanart": ("انتخاب فن‌آرت", "🎨"),
    "profile:titles": ("لقب‌ها", "🎖️"),
    "potion:choose:hp": ("بازیابی سلامت", "❤️"),
    "potion:choose:mana": ("بازیابی مانا", "💧"),
    "menu:back": ("بازگشت", "🔙"),
    "inventory:equipment": ("تجهیزات صندوقچه", "🛡️"),
    "inventory:scrolls": ("اسکرول‌ها", "📜"),
    "market:browse": ("مرور بازار", "🛍️"),
    "market:mine": ("آگهی‌های من", "📦"),
    "market:help": ("راهنمای بازار", "❔"),
    "guide:quick": ("راهنمای پیشرفت سریع", "⚡"),
    "guide:full": ("راهنمای جامع", "📚"),
    "party:members": ("اعضای پارتی", "👥"),
    "guild:members": ("اعضای گیلد", "👥"),
    "guild:missions": ("مأموریت‌های گیلد", "📜"),
    "guild:vault": ("خزانه گیلد", "🏦"),
    "worldboss:attack": ("حمله به باس", "⚔️"),
    "menu:worldboss": ("وضعیت باس", "🐉"),
}
# Categorized internal archive. Keys are real callback_data values.
INTERNAL_CATEGORIES = {
    "profile": ("👤 پروفایل", ["profile:stats", "potion:choose:hp", "potion:choose:mana", "profile:titles", "profile:fanart", "profile:clearfanart", "profile:setfanart:", "profile:settitle:", "profile:titlepage:"]),
    "inventory": ("🗃️ صندوقچه", ["inventory:equipment", "inventory:scrolls", "inventory:potions", "inventory:materials", "inventory:all", "inventory:fanart"]),
    "quest": ("📜 مأموریت‌ها", ["quest:list:story", "quest:list:daily", "quest:list:achievement", "quest:current_list", "quest:menu"]),
    "skills": ("✨ مهارت‌ها", ["skills:list", "skills:learn", "skills:upgrade"]),
    "equipment": ("🛡️ تجهیزات", ["equipment:list:weapon", "equipment:list:helmet", "equipment:list:armor", "equipment:list:boots", "equipment:list:ring", "equipment:list:necklace", "equipment:stats", "equipment:menu", "equipment:back"]),
    "shop": ("🛒 فروشگاه", ["shop:equipment", "shop:potion", "shop:material", "shop:scroll", "shop:gems", "shop:itemlist"]),
    "combat": ("⚔️ مبارزه", ["combat:attack:", "combat:skills:", "combat:potions:", "combat:flee:", "combat:back:", "combat:skill:", "combat:potion:"]),
    "social": ("👥 اجتماعی", ["party:members", "guild:members", "guild:missions", "guild:vault"]),
    "market": ("🏪 بازار", ["market:browse", "market:mine", "market:help"]),
    "guide": ("📖 راهنما", ["guide:quick", "guide:full"]),
    "other": ("⚙️ سایر", ["menu:back", "worldboss:attack", "menu:worldboss"]),
}
INTERNAL_BUTTONS.update({
    "profile:clearfanart": ("حذف فن‌آرت فعال", "🚫"),
    "profile:setfanart:": ("انتخاب فن‌آرت از فهرست", "🎨"),
    "profile:settitle:": ("انتخاب لقب از فهرست", "🎖️"),
    "profile:titlepage:": ("صفحه‌بندی لقب‌ها", "➡️"),
    "inventory:potions": ("معجون‌ها", "🧪"), "inventory:materials": ("متریال‌ها", "🗃️"),
    "inventory:all": ("همه آیتم‌های موجود", "📦"), "inventory:fanart": ("فن‌آرت‌های من", "🎨"),
    "quest:list:story": ("داستانی", "📖"), "quest:list:daily": ("روزانه", "📅"),
    "quest:list:achievement": ("دستاوردها", "🏆"), "quest:current_list": ("مأموریت‌های من", "📌"),
    "quest:menu": ("بازگشت به مأموریت‌ها", "🔙"),
    "skills:list": ("مهارت‌های من", "📚"), "skills:learn": ("یادگیری مهارت", "✨"),
    "skills:upgrade": ("ارتقای مهارت", "⬆️"),
    "equipment:list:weapon": ("سلاح‌ها", "⚔️"), "equipment:list:helmet": ("کلاه‌ها", "🪖"),
    "equipment:list:armor": ("زره‌ها", "🛡️"), "equipment:list:boots": ("کفش‌ها", "👢"),
    "equipment:list:ring": ("انگشترها", "💍"), "equipment:list:necklace": ("گردنبندها", "📿"),
    "equipment:stats": ("آمار تجهیزات", "📊"), "equipment:menu": ("بازگشت به تجهیزات", "🔙"),
    "equipment:back": ("بازگشت به منوی اصلی", "🔙"),
    "shop:equipment": ("تجهیزات فروشگاه", "⚔️"), "shop:potion": ("معجون‌های فروشگاه", "🧪"),
    "shop:material": ("متریال فروشگاه", "🗃️"), "shop:scroll": ("اسکرول‌های فروشگاه", "📜"),
    "shop:gems": ("فروشگاه ویژه جم", "💎"), "shop:itemlist": ("بازگشت به لیست فروشگاه", "🔙"),
    "combat:attack:": ("حمله", "⚔️"), "combat:skills:": ("مهارت‌های مبارزه", "🔮"),
    "combat:potions:": ("معجون مبارزه", "🧪"), "combat:flee:": ("فرار", "🏃"),
    "combat:back:": ("بازگشت به مبارزه", "🔙"), "combat:skill:": ("استفاده از مهارت", "✨"),
    "combat:potion:": ("استفاده از معجون", "🧪"),
})
ALL_BUTTONS = {**MAIN_BUTTONS, **INTERNAL_BUTTONS}
DEFAULTS = {key: value[1] for key, value in ALL_BUTTONS.items()}
_RUNTIME_CONFIG: dict[str, Any] | None = None
_CONFIG_LOCK = RLock()


def _locked(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with _CONFIG_LOCK:
            return func(*args, **kwargs)
    return wrapper


def _empty_config() -> dict[str, Any]:
    return {"version": 2, "enabled": True, "overrides": {}, "custom_emoji_ids": {}}


def _normalize_config(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _empty_config()
    overrides = data.get("overrides", {})
    custom_ids = data.get("custom_emoji_ids", {})
    overrides = overrides if isinstance(overrides, dict) else {}
    custom_ids = dict(custom_ids) if isinstance(custom_ids, dict) else {}
    clean_overrides = {}
    for key, value in overrides.items():
        if key not in ALL_BUTTONS:
            continue
        if isinstance(value, dict):
            if value.get("custom_emoji_id"):
                custom_ids[key] = value["custom_emoji_id"]
            value = value.get("emoji")
        if isinstance(value, str) and 0 < len(value.strip()) <= 16:
            clean_overrides[key] = value.strip()
    return {
        "version": 2,
        "enabled": data.get("enabled") if isinstance(data.get("enabled"), bool) else True,
        "overrides": clean_overrides,
        "custom_emoji_ids": {
            k: str(v) for k, v in custom_ids.items()
            if k in ALL_BUTTONS and str(v).isascii() and str(v).isdigit() and str(v).strip("0")
        },
    }


@_locked
def load_config() -> dict[str, Any]:
    try:
        return _normalize_config(json.loads(DATA_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return _empty_config()


@_locked
def save_config(config: dict[str, Any]) -> None:
    global _RUNTIME_CONFIG
    safe = _normalize_config(config)
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    # A unique temporary file avoids concurrent writers renaming the same file.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=DATA_FILE.parent,
                                         prefix=DATA_FILE.name + ".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(safe, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(DATA_FILE)
        _RUNTIME_CONFIG = safe
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@_locked
def _get_runtime_config() -> dict[str, Any]:
    global _RUNTIME_CONFIG
    if _RUNTIME_CONFIG is None:
        _RUNTIME_CONFIG = load_config()
    return _RUNTIME_CONFIG


def _callback_key(callback_data: str) -> str:
    if callback_data in ALL_BUTTONS:
        return callback_data
    return max((key for key in ALL_BUTTONS if key.endswith(":") and callback_data.startswith(key)),
               key=len, default=callback_data)


def get_emoji(callback_data: str) -> str | None:
    callback_data = _callback_key(callback_data)
    config = _get_runtime_config()
    if not config["enabled"]:
        return None
    return config["overrides"].get(callback_data, DEFAULTS.get(callback_data))


def get_custom_emoji_id(callback_data: str) -> str | None:
    callback_data = _callback_key(callback_data)
    config = _get_runtime_config()
    if not config["enabled"]:
        return None
    return config["custom_emoji_ids"].get(callback_data)


@_locked
def set_emoji(callback_data: str, emoji: str, custom_emoji_id: str | None = None) -> None:
    if callback_data not in ALL_BUTTONS:
        raise ValueError("Unknown button callback")
    value = emoji.strip() if isinstance(emoji, str) else ""
    if not value or len(value) > 16:
        raise ValueError("Emoji must be a short non-empty string")
    config = load_config()
    config["overrides"][callback_data] = value
    if custom_emoji_id and str(custom_emoji_id).isdigit():
        config["custom_emoji_ids"][callback_data] = str(custom_emoji_id)
    else:
        config["custom_emoji_ids"].pop(callback_data, None)
    save_config(config)


@_locked
def reset_emoji(callback_data: str) -> None:
    config = load_config()
    config["overrides"].pop(callback_data, None)
    config["custom_emoji_ids"].pop(callback_data, None)
    save_config(config)


@_locked
def reset_all() -> None:
    save_config(_empty_config())
