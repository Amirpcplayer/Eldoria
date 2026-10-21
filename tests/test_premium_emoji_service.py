from services.premium_emoji_service import transform_text


def test_global_conversion_replaces_registered_fallbacks():
    data = {"enabled": True, "ids": {"gold": "12345", "health": "67890"}}
    text = "💰 طلا و ❤️ سلامتی"
    result = transform_text(text, data)
    assert '<tg-emoji emoji-id="12345">💰</tg-emoji>' in result
    assert '<tg-emoji emoji-id="67890">❤️</tg-emoji>' in result


def test_disabled_configuration_keeps_normal_emoji():
    text = "💰 ❤️"
    assert transform_text(text, {"enabled": False, "ids": {"gold": "12345"}}) == text


def test_missing_ids_fall_back_to_normal_emoji():
    text = "💰 🏆"
    assert transform_text(text, {"enabled": True, "ids": {"gold": "not-an-id"}}) == text


def test_existing_custom_emoji_is_not_nested():
    text = '<tg-emoji emoji-id="12345">💰</tg-emoji> 💰'
    result = transform_text(text, {"enabled": True, "ids": {"gold": "12345"}})
    assert result.count('<tg-emoji') == 2
    assert '<tg-emoji emoji-id="12345"><tg-emoji' not in result


def test_dynamic_emoji_is_discovered_and_added_to_catalog(tmp_path, monkeypatch):
    import services.premium_emoji_service as service

    monkeypatch.setattr(service, "PATH", tmp_path / "premium_emojis.json")
    service.save({"enabled": False, "ids": {}, "catalog": {}})
    service.register_emojis("🧙‍♀️ and 🦄")
    data = service.load()
    assert "🧙‍♀️" in data["catalog"].values()
    assert "🦄" in data["catalog"].values()


def test_extract_emoji_keeps_joined_and_flag_sequences_together():
    from services.premium_emoji_service import extract_emojis

    assert extract_emojis("🧙‍♀️ 🇩🇪 1️⃣") == ["🧙‍♀️", "🇩🇪", "1️⃣"]


def test_dynamic_registered_emoji_can_be_converted(tmp_path, monkeypatch):
    import services.premium_emoji_service as service

    monkeypatch.setattr(service, "PATH", tmp_path / "premium_emojis.json")
    key = service._key_for_emoji("🦄")
    service.save({"enabled": True, "ids": {key: "99999"}, "catalog": {key: "🦄"}})
    assert '<tg-emoji emoji-id="99999">🦄</tg-emoji>' in service.transform_text("🦄")


def test_keyboard_button_uses_registered_custom_emoji_icon():
    from types import SimpleNamespace
    from services.premium_emoji_service import apply_keyboard_icons

    button = SimpleNamespace(text="🏆 رتبه‌بندی", icon_custom_emoji_id=None, callback_data="rank")
    markup = SimpleNamespace(inline_keyboard=[[button]])
    data = {"enabled": True, "ids": {"rank": "777"}, "catalog": {}}
    apply_keyboard_icons(markup, data)
    assert button.icon_custom_emoji_id == "777"
    assert button.text == "رتبه‌بندی"


def test_reply_keyboard_button_label_is_preserved_for_handler_matching():
    from types import SimpleNamespace
    from services.premium_emoji_service import apply_keyboard_icons

    button = SimpleNamespace(text="🏆 رتبه‌بندی", icon_custom_emoji_id=None)
    markup = SimpleNamespace(keyboard=[[button]])
    data = {"enabled": True, "ids": {"rank": "777"}, "catalog": {}}
    apply_keyboard_icons(markup, data)
    assert button.icon_custom_emoji_id == "777"
    assert button.text == "🏆 رتبه‌بندی"


def test_catalog_has_one_row_for_repeated_emoji_and_selector_variants(tmp_path, monkeypatch):
    import services.premium_emoji_service as service

    monkeypatch.setattr(service, "PATH", tmp_path / "premium_emojis.json")
    service.save({"enabled": False, "ids": {}, "catalog": {}})
    service.register_emojis("❤️ ❤️ ❤ ❤️")
    items = service.catalog_items(service.load())
    hearts = [(key, value) for key, value in items if service._canonical_emoji(value) == "❤"]
    assert len(hearts) == 1


def test_one_premium_id_replaces_all_observed_variants_globally(tmp_path, monkeypatch):
    import services.premium_emoji_service as service

    monkeypatch.setattr(service, "PATH", tmp_path / "premium_emojis.json")
    key = "health"
    service.save({"enabled": True, "ids": {key: "54321"}, "catalog": {}, "aliases": {key: ["❤️", "❤"]}})
    result = service.transform_text("❤️ ❤ ❤️", service.load())
    assert result.count('emoji-id="54321"') == 3


def test_emoji_only_inline_button_never_becomes_empty():
    from types import SimpleNamespace
    from services.premium_emoji_service import apply_keyboard_icons

    button = SimpleNamespace(text="🏆", icon_custom_emoji_id=None, callback_data="rank")
    markup = SimpleNamespace(inline_keyboard=[[button]])
    data = {"enabled": True, "ids": {"rank": "777"}, "catalog": {}}
    apply_keyboard_icons(markup, data)
    assert button.icon_custom_emoji_id == "777"
    assert button.text == "🏆"
    assert button.text.strip() != ""
