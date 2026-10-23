from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.premium_emoji_service import load


PROFILE_BUTTONS = (
    ("profile_inventory", "🗃️", "صندوقچه", "menu:inventory"),
    ("profile_equipment", "🗡️", "تجهیزات", "menu:equipment"),
    ("profile_skills", "⚔️", "مهارت‌ها", "menu:skills"),
    ("profile_stats", "📊", "آمار کامل", "profile:stats"),
    ("profile_fanart_select", "🎨", "Fan Art پروفایل", "profile:fanart"),
    ("profile_back", "🔙", "بازگشت", "menu:back"),
)


def _profile_button(key: str, fallback_emoji: str, label: str, callback_data: str) -> InlineKeyboardButton:
    data = load()
    emoji_id = str(data.get("ids", {}).get(key, "") or "")
    enabled = bool(data.get("enabled")) and emoji_id.isdigit()

    # Apply the configured icon while constructing the keyboard itself.
    # This makes profile buttons independent of text/callback heuristics in
    # the outgoing-request middleware.
    if enabled:
        return InlineKeyboardButton(
            text=label,
            callback_data=callback_data,
            icon_custom_emoji_id=emoji_id,
        )

    return InlineKeyboardButton(
        text=f"{fallback_emoji} {label}",
        callback_data=callback_data,
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        _profile_button(key, glyph, label, callback)
        for key, glyph, label, callback in PROFILE_BUTTONS
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            buttons[0:2],
            buttons[2:4],
            buttons[4:5],
            buttons[5:6],
        ]
    )
