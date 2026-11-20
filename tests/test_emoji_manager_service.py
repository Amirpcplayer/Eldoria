from __future__ import annotations

import json

import pytest

import services.emoji_manager_service as service


def test_defaults_cover_all_registered_buttons():
    assert service.DEFAULTS
    assert set(service.DEFAULTS) == set(service.ALL_BUTTONS)
    assert all(isinstance(value, str) and value.strip() for value in service.DEFAULTS.values())


def test_missing_or_invalid_config_falls_back_to_safe_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DATA_FILE", tmp_path / "missing.json")
    assert service.load_config() == service._empty_config()
    service.DATA_FILE.write_text("{broken", encoding="utf-8")
    assert service.load_config() == service._empty_config()


def test_config_filters_unknown_keys_and_invalid_custom_emoji_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DATA_FILE", tmp_path / "emoji.json")
    service.DATA_FILE.write_text(json.dumps({
        "enabled": True,
        "overrides": {"menu:profile": "🧙", "not-a-button": "❌"},
        "custom_emoji_ids": {"menu:profile": "12345", "menu:skills": "bad", "unknown": "7"},
    }), encoding="utf-8")
    config = service.load_config()
    assert config["overrides"] == {"menu:profile": "🧙"}
    assert config["custom_emoji_ids"] == {"menu:profile": "12345"}


def test_set_and_reset_emoji_persist_safely(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DATA_FILE", tmp_path / "emoji.json")
    monkeypatch.setattr(service, "_RUNTIME_CONFIG", None)
    service.set_emoji("menu:profile", "🧙", "12345")
    assert service.load_config()["overrides"]["menu:profile"] == "🧙"
    assert service.load_config()["custom_emoji_ids"]["menu:profile"] == "12345"
    service.reset_emoji("menu:profile")
    assert "menu:profile" not in service.load_config()["overrides"]
    assert "menu:profile" not in service.load_config()["custom_emoji_ids"]


def test_unknown_callback_and_empty_emoji_are_rejected():
    with pytest.raises(ValueError):
        service.set_emoji("unknown:callback", "🧙")
    with pytest.raises(ValueError):
        service.set_emoji("menu:profile", "  ")
