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
    service.set_start_emoji_id("gender_check", "987654321")
    service.set_start_emoji_id("gender_male_button", "111222333")
    service.set_start_emoji_id("race_dna", "444555666")
    service.set_start_emoji_id("global_back_button", "777888999")
    service.set_start_emoji_id("race_confirm_button", "222333444")
    service.set_start_emoji_id("race_enter_game_button", "555666777")
    assert service.get_start_emoji_ids() == {
        "sword": "123456789",
        "gender_check": "987654321",
        "gender_male_button": "111222333",
        "race_dna": "444555666",
        "global_back_button": "777888999",
        "race_confirm_button": "222333444",
        "race_enter_game_button": "555666777",
    }
    assert service.render_start_emoji("sword", "⚔️") == '<tg-emoji emoji-id="123456789">⚔️</tg-emoji>'
    assert service.render_start_emoji("scroll", "📜") == "📜"
    assert service.render_start_emoji("gender_check", "✅") == '<tg-emoji emoji-id="987654321">✅</tg-emoji>'
    assert service.render_start_emoji("race_dna", "🧬") == '<tg-emoji emoji-id="444555666">🧬</tg-emoji>'


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("unknown", "123"),
        ("gender_symbol", "not-an-id"),
        ("race_werewolf_button", "not-an-id"),
        ("global_back_button", "not-an-id"),
        ("race_confirm_button", "not-an-id"),
        ("race_enter_game_button", "not-an-id"),
        ("sword", "abc"),
        ("pen", ""),
        ("scroll", "000"),
    ],
)
def test_rejects_invalid_ids(tmp_path, monkeypatch, key, value):
    monkeypatch.setattr(service, "DATA_FILE", tmp_path / "start.json")
    with pytest.raises(ValueError):
        service.set_start_emoji_id(key, value)
