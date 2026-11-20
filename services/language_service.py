from __future__ import annotations

# World Eldoria is Persian-only. There is no player language preference or
# language-switching feature. These helpers remain as a compatibility layer for
# existing handlers and always resolve to Persian.
PERSIAN_TEXT = {
    "main_title": "🎮 <b>منوی اصلی World Eldoria</b>",
    "main_sub": "🌌 ماجراجویی تو در اِلدوریا ادامه دارد...",
    "settings": "⚙️ <b>تنظیمات اِلدوریا</b>\n\nتنظیمات بازیکن خود را مدیریت کن.",
    "settings_button": "⚙️ تنظیمات",
    "rename": "✍️ تغییر نام قهرمان · ۲٬۰۰۰ Gold",
    "back": "🔙 بازگشت",
    "profile": "👤 پروفایل",
    "inventory": "🗃 صندوقچه",
    "skills": "⚔️ مهارت‌ها",
    "equipment": "🛡️ تجهیزات",
    "quest": "📜 مأموریت‌ها",
    "adventure": "🗺️ ماجراجویی",
    "crafting": "🔨 کرفتینگ",
    "pets": "🐾 پت",
    "events": "🎉 ایونت",
    "party": "👥 پارتی",
    "guild": "🛡️ گیلد",
    "ranking": "🏆 رتبه‌بندی",
    "forge": "⚒️ آهنگری",
    "marketplace": "🏪 بازار بازیکنان",
    "bestiary": "📖 دفترچهٔ هیولا",
    "exchange": "💱 تبدیل گلد به جم",
    "guide": "📖 راهنما",
    "shop": "🛒 فروشگاه",
}


async def get_language(telegram_id: int) -> str:
    """Return the fixed game language; no per-player setting is read or stored."""
    return "fa"


def tr(language: str, key: str) -> str:
    """Compatibility translator that always returns Persian text."""
    return PERSIAN_TEXT.get(key, key)
