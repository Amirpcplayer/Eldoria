"""Shared potion catalog and recovery rules for World Eldoria."""
from __future__ import annotations

POTION_SHOP_ITEMS = {
    "🧪 معجون سلامتی": {"kind": "hp", "ratio": 0.20},
    "🧪 معجون سلامتی بزرگ": {"kind": "hp", "ratio": 0.40},
    "🔷 معجون مانا": {"kind": "mana", "ratio": 0.20},
    "🧪 معجون مانای بزرگ": {"kind": "mana", "ratio": 0.40},
}

BIG_POTION_TOKENS = (
    "بزرگ", "large", "ممتاز", "افسانه", "اسطوره", "کهن", "ابدی",
    "قهرمان", "legendary", "mythic", "divine", "epic",
)


def potion_kind(name: str) -> str | None:
    lowered = str(name).lower()
    if "مانا" in lowered or "mana" in lowered or "جادو" in lowered:
        return "mana"
    if any(token in lowered for token in ("hp", "سلامتی", "health")):
        return "hp"
    return None


def potion_restore_ratio(name: str) -> float:
    """Small/ordinary potions restore 20%; large tiers restore 40%."""
    lowered = str(name).lower()
    return 0.40 if any(token in lowered for token in BIG_POTION_TOKENS) else 0.20


def is_shop_potion(name: str) -> bool:
    return str(name) in POTION_SHOP_ITEMS
