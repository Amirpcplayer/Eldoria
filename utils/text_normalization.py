"""Small, dependency-free text normalization helpers for Persian UI and filters."""

from __future__ import annotations

import re


_FILTER_TRANSLATION = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ـ": ""})


def normalize_filter_text(value: str) -> str:
    """Normalize common Arabic/Persian spelling variants for group word filters."""
    value = (value or "").casefold().translate(_FILTER_TRANSLATION)
    value = re.sub(r"[\u064B-\u065F\u0670]", "", value)
    value = value.replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    return re.sub(r"\s+", " ", value).strip()
