from __future__ import annotations

import json
from pathlib import Path
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
    "inventory:all": ("همه آیتم‌ها", "📦"), "inventory:fanart": ("فن‌آرت‌های من", "🎨"),
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


def _empty_config() -> dict[str, Any]:
    return {"version": 2, "enabled": True, "overrides": {}, "custom_emoji_ids": {}}


def load_config() -> dict[str, Any]:
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        overrides = data.get("overrides", {})
        custom_ids = data.get("custom_emoji_ids", {})
        if not isinstance(overrides, dict):
            overrides = {}
        if not isinstance(custom_ids, dict):
            custom_ids = {}
        clean_overrides: dict[str, str] = {}
        for key, value in overrides.items():
            if key not in ALL_BUTTONS:
                continue
            # Migrate the old string format and accept the new structured format.
            if isinstance(value, str) and value:
                clean_overrides[str(key)] = value
            elif isinstance(value, dict) and isinstance(value.get("emoji"), str) and value["emoji"]:
                clean_overrides[str(key)] = value["emoji"]
                if value.get("custom_emoji_id"):
                    custom_ids[str(key)] = str(value["custom_emoji_id"])
        return {
            "version": 2,
            "enabled": bool(data.get("enabled", True)),
            "overrides": clean_overrides,
            "custom_emoji_ids": {
                str(k): str(v) for k, v in custom_ids.items()
                if k in ALL_BUTTONS and str(v).isdigit()
            },
        }
    except (OSError, ValueError, TypeError):
        return _empty_config()


def save_config(config: dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    safe = {
        "version": 2,
        "enabled": bool(config.get("enabled", True)),
        "overrides": {
            str(k): str(v) for k, v in config.get("overrides", {}).items()
            if k in ALL_BUTTONS and isinstance(v, str) and v
        },
        "custom_emoji_ids": {
            str(k): str(v) for k, v in config.get("custom_emoji_ids", {}).items()
            if k in ALL_BUTTONS and str(v).isdigit()
        },
    }
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATA_FILE)


def _get_runtime_config() -> dict[str, Any]:
    global _RUNTIME_CONFIG
    if _RUNTIME_CONFIG is None:
        _RUNTIME_CONFIG = load_config()
    return _RUNTIME_CONFIG


def get_emoji(callback_data: str) -> str | None:
    config = _get_runtime_config()
    if not config["enabled"]:
        return None
    return config["overrides"].get(callback_data, DEFAULTS.get(callback_data))


def get_custom_emoji_id(callback_data: str) -> str | None:
    config = _get_runtime_config()
    if not config["enabled"]:
        return None
    return config["custom_emoji_ids"].get(callback_data)


def set_emoji(callback_data: str, emoji: str, custom_emoji_id: str | None = None) -> None:
    if callback_data not in ALL_BUTTONS:
        raise ValueError("Unknown button callback")
    value = emoji.strip()
    if not value or len(value) > 16:
        raise ValueError("Emoji must be a short non-empty string")
    config = load_config()
    config["overrides"][callback_data] = value
    if custom_emoji_id and str(custom_emoji_id).isdigit():
        config["custom_emoji_ids"][callback_data] = str(custom_emoji_id)
    else:
        config["custom_emoji_ids"].pop(callback_data, None)
    save_config(config)
    global _RUNTIME_CONFIG
    _RUNTIME_CONFIG = config


def reset_emoji(callback_data: str) -> None:
    config = load_config()
    config["overrides"].pop(callback_data, None)
    config["custom_emoji_ids"].pop(callback_data, None)
    save_config(config)
    global _RUNTIME_CONFIG
    _RUNTIME_CONFIG = config


def reset_all() -> None:
    config = _empty_config()
    save_config(config)
    global _RUNTIME_CONFIG
    _RUNTIME_CONFIG = config
