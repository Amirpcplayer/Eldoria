from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "start_premium_emojis.json"
_ALLOWED_KEYS = {
    "sword", "scroll", "pen",
    "gender_check", "gender_sword", "gender_symbol",
    "gender_male_button", "gender_female_button",
    "race_check", "race_moon", "race_dna",
    "race_human_button", "race_elf_button", "race_demon_button",
    "race_dwarf_button", "race_fairy_button", "race_dragonite_button",
    "race_werewolf_button", "race_vampire_button",
}
_LOCK = RLock()


def get_start_emoji_ids() -> dict[str, str]:
    with _LOCK:
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            key: str(value)
            for key, value in data.items()
            if key in _ALLOWED_KEYS
            and str(value).isascii()
            and str(value).isdigit()
            and str(value).strip("0")
        }


def set_start_emoji_id(key: str, custom_emoji_id: str) -> None:
    value = str(custom_emoji_id)
    if (
        key not in _ALLOWED_KEYS
        or not value.isascii()
        or not value.isdigit()
        or not value.strip("0")
    ):
        raise ValueError("Invalid start custom emoji")
    with _LOCK:
        values = get_start_emoji_ids()
        values[key] = value
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=DATA_FILE.parent,
                prefix=DATA_FILE.name + ".",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                json.dump(values, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(DATA_FILE)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def render_start_emoji(key: str, fallback: str) -> str:
    if key not in _ALLOWED_KEYS:
        raise ValueError("Unknown start emoji key")
    custom_id = get_start_emoji_ids().get(key)
    if not custom_id:
        return fallback
    return f'<tg-emoji emoji-id="{custom_id}">{fallback}</tg-emoji>'
