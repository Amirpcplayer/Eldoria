from __future__ import annotations

import pytest

import services.start_premium_emoji_service as service


def test_missing_or_invalid_file_returns_empty_config(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DATA_FILE", tmp_path / "start.json")
    assert service.get_start_emoji_ids() == {}
    service.DATA_FILE.write_text("{broken", encoding="utf-8")
    assert service.get_start_emoji_ids() == {}


def test_set_and_render_custom_emoji(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DATA_FILE", tmp_path / "start.json")
    service.set_start_emoji_id("sword", "123456789")
    assert service.get_start_emoji_ids() == {"sword": "123456789"}
    assert service.render_start_emoji("sword", "⚔️") == '<tg-emoji emoji-id="123456789">⚔️</tg-emoji>'
    assert service.render_start_emoji("scroll", "📜") == "📜"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("unknown", "123"),
        ("sword", "abc"),
        ("pen", ""),
        ("scroll", "000"),
    ],
)
def test_rejects_invalid_ids(tmp_path, monkeypatch, key, value):
    monkeypatch.setattr(service, "DATA_FILE", tmp_path / "start.json")
    with pytest.raises(ValueError):
        service.set_start_emoji_id(key, value)
