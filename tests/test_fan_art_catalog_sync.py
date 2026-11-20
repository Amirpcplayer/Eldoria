from __future__ import annotations

import pytest

from models.fan_art import FanArt
from sync_catalogs import CATALOGS, _check_fan_art_catalog


def test_fan_art_is_in_catalog_totals() -> None:
    assert ("Fan Art catalog entries", FanArt) in CATALOGS


@pytest.mark.asyncio
async def test_empty_fan_art_catalog_explains_admin_setup(capsys) -> None:
    await _check_fan_art_catalog()
    output = capsys.readouterr().out
    assert "Fan Art catalog status" in output
    assert "/fanart_add" in output
    assert "real Telegram photo file_id" in output
