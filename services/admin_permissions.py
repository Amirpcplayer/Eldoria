"""Persistent delegated-admin permissions for the Telegram bot.

Stored separately from the main database so the admin panel can start even when
no dedicated SQL model exists for delegated admins.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
_FILE = Path(__file__).resolve().parent.parent / "data" / "delegated_admins.json"
_LOCK = asyncio.Lock()


def _read_ids() -> set[int]:
    try:
        raw = json.loads(_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return set()
        return {int(value) for value in raw if str(value).lstrip("-").isdigit()}
    except FileNotFoundError:
        return set()
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        logger.exception("Could not read delegated admin list")
        return set()


def _write_ids(ids: set[int]) -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = _FILE.with_suffix(".json.tmp")
    temp_file.write_text(
        json.dumps(sorted(ids), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_file.replace(_FILE)


async def add_delegated_admin(telegram_id: int) -> None:
    async with _LOCK:
        ids = _read_ids()
        ids.add(int(telegram_id))
        _write_ids(ids)


async def remove_delegated_admin(telegram_id: int) -> None:
    async with _LOCK:
        ids = _read_ids()
        ids.discard(int(telegram_id))
        _write_ids(ids)


async def is_delegated_admin(telegram_id: int) -> bool:
    async with _LOCK:
        return int(telegram_id) in _read_ids()


async def list_delegated_admins() -> list[int]:
    async with _LOCK:
        return sorted(_read_ids())
