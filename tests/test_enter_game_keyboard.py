from keyboards.main_menu import enter_game_keyboard


def test_enter_game_keyboard_accepts_language_argument():
    keyboard = enter_game_keyboard("fa")
    button = keyboard.inline_keyboard[0][0]
    assert button.callback_data == "menu:enter_game"
    assert button.text == "🎮 ورود به بازی"


def test_enter_game_keyboard_localizes_supported_languages():
    assert enter_game_keyboard("en").inline_keyboard[0][0].text == "🎮 Enter the Game"
    assert enter_game_keyboard("ru").inline_keyboard[0][0].text == "🎮 Войти в игру"


def test_enter_game_keyboard_falls_back_to_persian_for_unknown_language():
    assert enter_game_keyboard("xx").inline_keyboard[0][0].text == "🎮 ورود به بازی"


def test_enter_game_keyboard_keeps_backward_compatible_default():
    assert enter_game_keyboard().inline_keyboard[0][0].text == "🎮 ورود به بازی"
