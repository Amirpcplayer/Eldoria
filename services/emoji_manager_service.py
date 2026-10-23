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
ALL_BUTTONS = {**MAIN_BUTTONS, **INTERNAL_BUTTONS}
DEFAULTS = {key: value[1] for key, value in ALL_BUTTONS.items()}


def load_config() -> dict[str, Any]:
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        overrides = data.get("overrides", {})
        if not isinstance(overrides, dict):
            overrides = {}
        return {"version": 1, "enabled": bool(data.get("enabled", True)),
                "overrides": {str(k): str(v) for k, v in overrides.items()
                              if k in ALL_BUTTONS and isinstance(v, str) and v}}
    except (OSError, ValueError, TypeError):
        return {"version": 1, "enabled": True, "overrides": {}}


def save_config(config: dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    safe = {"version": 1, "enabled": bool(config.get("enabled", True)),
            "overrides": {str(k): str(v) for k, v in config.get("overrides", {}).items()
                          if k in ALL_BUTTONS and isinstance(v, str) and v}}
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATA_FILE)


def get_emoji(callback_data: str) -> str | None:
    config = load_config()
    if not config["enabled"]:
        return None
    return config["overrides"].get(callback_data, DEFAULTS.get(callback_data))


def set_emoji(callback_data: str, emoji: str) -> None:
    if callback_data not in ALL_BUTTONS:
        raise ValueError("Unknown button callback")
    value = emoji.strip()
    if not value or len(value) > 16:
        raise ValueError("Emoji must be a short non-empty string")
    config = load_config()
    config["overrides"][callback_data] = value
    save_config(config)


def reset_emoji(callback_data: str) -> None:
    config = load_config()
    config["overrides"].pop(callback_data, None)
    save_config(config)


def reset_all() -> None:
    save_config({"version": 1, "enabled": True, "overrides": {}})
