from keyboards.main_menu import main_menu_keyboard


def _buttons(keyboard):
    return [button for row in keyboard.inline_keyboard for button in row]


def test_main_menu_keyboard_accepts_language_argument():
    keyboard = main_menu_keyboard("fa")
    buttons = _buttons(keyboard)
    assert any(button.text == "⚙️ تنظیمات" and button.callback_data == "menu:settings" for button in buttons)


def test_main_menu_keyboard_localizes_supported_languages():
    en = _buttons(main_menu_keyboard("en"))
    ru = _buttons(main_menu_keyboard("ru"))
    assert any(button.text == "⚙️ Settings" and button.callback_data == "menu:settings" for button in en)
    assert any(button.text == "⚙️ Настройки" and button.callback_data == "menu:settings" for button in ru)


def test_main_menu_keyboard_falls_back_and_keeps_no_arg_compatibility():
    default_buttons = _buttons(main_menu_keyboard())
    fallback_buttons = _buttons(main_menu_keyboard("unknown"))
    assert [b.text for b in default_buttons] == [b.text for b in fallback_buttons]
    assert len(default_buttons) == 19
