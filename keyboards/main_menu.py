from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(language: str = "fa") -> InlineKeyboardMarkup:
    """Build the main menu keyboard in the requested language.

    Keep the default Persian label set for existing callers that do not pass a
    language, while supporting the localized entry flow in handlers/element.py.
    Callback data intentionally stays language-independent.
    """
    language = (language or "fa").lower().split("-", 1)[0]
    labels = {
        "fa": {
            "profile": "👤 پروفایل", "inventory": "🗃 صندوقچه",
            "skills": "⚔️ مهارت‌ها", "equipment": "🛡️ تجهیزات",
            "quests": "📜 ماموریت‌ها", "adventure": "🗺️ ماجراجویی",
            "crafting": "🔨 کرفتینگ", "pets": "🐾 پت", "events": "🎉 ایونت",
            "party": "👥 پارتی", "guild": "🛡️ گیلد", "ranking": "🏆 رتبه‌بندی",
            "forge": "⚒️ آهنگری", "marketplace": "🏪 بازار بازیکنان",
            "bestiary": "📖 دفترچه هیولا", "exchange": "💱 تبدیل گلد به جم",
            "guide": "📖 راهنما", "shop": "🛒 فروشگاه", "settings": "⚙️ تنظیمات",
        },
        "en": {
            "profile": "👤 Profile", "inventory": "🗃 Inventory",
            "skills": "⚔️ Skills", "equipment": "🛡️ Equipment",
            "quests": "📜 Quests", "adventure": "🗺️ Adventure",
            "crafting": "🔨 Crafting", "pets": "🐾 Pets", "events": "🎉 Events",
            "party": "👥 Party", "guild": "🛡️ Guild", "ranking": "🏆 Rankings",
            "forge": "⚒️ Forge", "marketplace": "🏪 Player Market",
            "bestiary": "📖 Monster Codex", "exchange": "💱 Gold to Gems",
            "guide": "📖 Guide", "shop": "🛒 Shop", "settings": "⚙️ Settings",
        },
        "ru": {
            "profile": "👤 Профиль", "inventory": "🗃 Сундук",
            "skills": "⚔️ Навыки", "equipment": "🛡️ Снаряжение",
            "quests": "📜 Задания", "adventure": "🗺️ Приключения",
            "crafting": "🔨 Ремесло", "pets": "🐾 Питомцы", "events": "🎉 События",
            "party": "👥 Отряд", "guild": "🛡️ Гильдия", "ranking": "🏆 Рейтинг",
            "forge": "⚒️ Кузница", "marketplace": "🏪 Рынок игроков",
            "bestiary": "📖 Бестиарий", "exchange": "💱 Золото в самоцветы",
            "guide": "📖 Руководство", "shop": "🛒 Магазин", "settings": "⚙️ Настройки",
        },
    }.get(language, None)
    if labels is None:
        labels = {
            "profile": "👤 پروفایل", "inventory": "🗃 صندوقچه",
            "skills": "⚔️ مهارت‌ها", "equipment": "🛡️ تجهیزات",
            "quests": "📜 ماموریت‌ها", "adventure": "🗺️ ماجراجویی",
            "crafting": "🔨 کرفتینگ", "pets": "🐾 پت", "events": "🎉 ایونت",
            "party": "👥 پارتی", "guild": "🛡️ گیلد", "ranking": "🏆 رتبه‌بندی",
            "forge": "⚒️ آهنگری", "marketplace": "🏪 بازار بازیکنان",
            "bestiary": "📖 دفترچه هیولا", "exchange": "💱 تبدیل گلد به جم",
            "guide": "📖 راهنما", "shop": "🛒 فروشگاه", "settings": "⚙️ تنظیمات",
        }

    def button(key: str, callback_data: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=labels[key], callback_data=callback_data)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button("profile", "menu:profile"), button("inventory", "menu:inventory")],
            [button("skills", "menu:skills"), button("equipment", "menu:equipment")],
            [button("quests", "menu:quest"), button("adventure", "menu:adventure")],
            [button("crafting", "menu:crafting")],
            [button("pets", "menu:pets"), button("events", "menu:events")],
            [button("party", "menu:party")],
            [button("guild", "menu:guild"), button("ranking", "menu:ranking")],
            [button("forge", "menu:forge"), button("marketplace", "menu:marketplace")],
            [button("bestiary", "menu:bestiary")],
            [button("exchange", "menu:exchange"), button("guide", "menu:guide")],
            [button("shop", "menu:shop")],
            [button("settings", "menu:settings")],
        ]
    )


def enter_game_keyboard(language: str = "fa") -> InlineKeyboardMarkup:
    """Return the post-character-creation button in the user's language.

    The default remains Persian for backward compatibility with existing callers.
    """
    language = (language or "fa").lower().split("-", 1)[0]
    button_text = {
        "en": "🎮 Enter the Game",
        "fa": "🎮 ورود به بازی",
        "ru": "🎮 Войти в игру",
    }.get(language, "🎮 ورود به بازی")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text, callback_data="menu:enter_game")]
    ])
