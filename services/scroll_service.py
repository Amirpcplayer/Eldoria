"""Timed effects and consumable scroll definitions for Eldoria."""
from __future__ import annotations

import json
from datetime import datetime

from database.redis import redis

DURATION_SECONDS = 2 * 60 * 60

SCROLLS = {
    "power": {
        "names": ("📜 اسکرول قدرت", "طومار قدرت"),
        "title": "قدرت",
        "description": "به مدت ۲ ساعت، آسیب حملات فیزیکی و جادویی را ۲۰٪ افزایش می‌دهد.",
        "duration": True,
    },
    "skill_power": {
        "names": ("📜 طومار مهارت", "طومار مهارت", "اسکرول مهارت"),
        "title": "تقویت مهارت جادویی",
        "description": "به مدت ۲ ساعت، آسیب واردشده با مهارت‌های جادویی را ۲۰٪ افزایش می‌دهد.",
        "duration": True,
    },
    "experience": {
        "names": ("📜 طومار تجربه", "طومار تجربه", "اسکرول تجربه"),
        "title": "تجربه",
        "description": "به‌محض استفاده، XP دریافت می‌کنی و تا ۲ ساعت XP جوایزت ۳۰٪ بیشتر می‌شود.",
        "duration": True,
        "xp_multiplier": 1.30,
        "instant_xp_per_level": 150,
    },
    "experience_small": {
        "names": ("📜 طومار تجربه کوچک", "طومار تجربه کوچک", "اسکرول تجربه کوچک"),
        "title": "تجربه کوچک",
        "description": "به‌محض استفاده، XP دریافت می‌کنی و تا ۲ ساعت XP جوایزت ۱۵٪ بیشتر می‌شود.",
        "duration": True,
        "xp_multiplier": 1.15,
        "instant_xp_per_level": 50,
    },
    "defense": {
        "names": ("📜 اسکرول دفاع", "طومار دفاع"),
        "title": "دفاع",
        "description": "به مدت ۲ ساعت، آسیب دریافتی از دشمنان را ۲۰٪ کاهش می‌دهد.",
        "duration": True,
    },
    "resistance": {
        "names": ("📜 اسکرول مقاومت", "طومار مقاومت"),
        "title": "مقاومت‌شکن",
        "description": "به مدت ۲ ساعت، مقاومت عنصری دشمن را هنگام جادو نادیده می‌گیرد.",
        "duration": True,
    },
    "healing": {
        "names": ("📜 اسکرول درمان", "طومار درمان"),
        "title": "درمان",
        "description": "به مدت ۲ ساعت، اثر بازیابی HP را ۲۰٪ افزایش می‌دهد.",
        "duration": True,
    },
    "mana": {
        "names": ("📜 اسکرول مانا", "طومار مانا"),
        "title": "مانا",
        "description": "به مدت ۲ ساعت، اثر بازیابی Mana را ۲۰٪ افزایش می‌دهد.",
        "duration": True,
    },
    "explorer": {
        "names": ("📜 اسکرول شکارچی", "📜 اسکرول کاوشگر", "طومار شکارچی", "طومار کاوشگر"),
        "title": "کاوشگر",
        "description": "به مدت ۲ ساعت، پاداش Gold و XP ماجراجویی و شانس یافتن متریال را ۳۰٪ افزایش می‌دهد.",
        "duration": True,
        "xp_multiplier": 1.30,
    },
}


def scroll_kind(item_name: str) -> str | None:
    """Map Persian/current/legacy scroll names to a supported effect."""
    normalized = " ".join(str(item_name or "").replace("📜", "").split()).casefold()
    if not normalized:
        return None

    # Check the most specific names first to avoid mapping the small XP scroll
    # to the regular XP scroll.
    for kind, data in sorted(
        SCROLLS.items(),
        key=lambda pair: max((len(name) for name in pair[1]["names"]), default=0),
        reverse=True,
    ):
        for known_name in data["names"]:
            known_normalized = " ".join(known_name.replace("📜", "").split()).casefold()
            if normalized == known_normalized or known_normalized in normalized:
                return kind

    aliases = {
        "power": ("اسکرول قدرت", "طومار قدرت"),
        "skill_power": ("طومار مهارت", "اسکرول مهارت", "مهارت"),
        "experience_small": ("طومار تجربه کوچک", "اسکرول تجربه کوچک", "تجربه کوچک"),
        "experience": ("طومار تجربه", "اسکرول تجربه", "تجربه"),
        "defense": ("اسکرول دفاع", "طومار دفاع"),
        "resistance": ("اسکرول مقاومت", "طومار مقاومت", "مقاومت شکن", "مقاومت‌شکن"),
        "healing": ("اسکرول درمان", "طومار درمان"),
        "mana": ("اسکرول مانا", "طومار مانا"),
        "explorer": ("اسکرول شکارچی", "طومار شکارچی", "اسکرول کاوشگر", "طومار کاوشگر", "کاوشگر"),
    }
    for kind, names in aliases.items():
        if any(name.casefold() in normalized for name in names):
            return kind
    return None


def buff_key(telegram_id: int, kind: str) -> str:
    return f"eldoria:scroll_buff:{int(telegram_id)}:{kind}"


async def get_buff(telegram_id: int, kind: str) -> dict | None:
    raw = await redis.get(buff_key(telegram_id, kind))
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if float(data.get("expires_at", 0)) <= datetime.utcnow().timestamp():
            await redis.delete(buff_key(telegram_id, kind))
            return None
        return data
    except (ValueError, TypeError, json.JSONDecodeError):
        await redis.delete(buff_key(telegram_id, kind))
        return None


async def has_buff(telegram_id: int, kind: str) -> bool:
    return await get_buff(telegram_id, kind) is not None


async def activate_scroll(telegram_id: int, kind: str) -> tuple[bool, str]:
    if kind not in SCROLLS:
        return False, "اثر این اسکرول هنوز تعریف نشده است."

    key = buff_key(telegram_id, kind)
    existing = await get_buff(telegram_id, kind)
    if existing:
        remaining = max(1, int(float(existing["expires_at"]) - datetime.utcnow().timestamp()))
        hours, minutes = divmod(remaining // 60, 60)
        return False, f"اثر «{SCROLLS[kind]['title']}» از قبل فعال است؛ زمان باقی‌مانده: {hours} ساعت و {minutes} دقیقه. اثرها روی هم انباشته نمی‌شوند."

    now = datetime.utcnow().timestamp()
    payload = {
        "kind": kind,
        "started_at": now,
        "expires_at": now + DURATION_SECONDS,
        "xp_multiplier": float(SCROLLS[kind].get("xp_multiplier", 1.0)),
    }
    await redis.set(key, json.dumps(payload), ex=DURATION_SECONDS, nx=True)
    confirmed = await get_buff(telegram_id, kind)
    if not confirmed or float(confirmed.get("started_at", 0)) != now:
        return False, "این اسکرول همین حالا فعال شده است؛ اثر تکراری اعمال نشد."
    return True, f"اسکرول «{SCROLLS[kind]['title']}» فعال شد و تا ۲ ساعت اثر دارد."
    
async def active_buffs(telegram_id: int) -> list[tuple[str, dict]]:
    result = []
    for kind in SCROLLS:
        buff = await get_buff(telegram_id, kind)
        if buff:
            result.append((kind, buff))
    return result
