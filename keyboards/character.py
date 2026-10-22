from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

_GENDER = {
    "fa": ("⚔️ مرد", "🌙 زن"),
    "en": ("⚔️ Male", "🌙 Female"),
    "ru": ("⚔️ Мужчина", "🌙 Женщина"),
}
_RACES = {
    "fa": ("👤 انسان", "🧝 الف", "😈 شیطان", "⛏️ دورف", "🐉 درگونایت", "🧚 پری", "🧛 خون‌آشام", "🐺 گرگینه"),
    "en": ("👤 Human", "🧝 Elf", "😈 Demon", "⛏️ Dwarf", "🐉 Dragonkin", "🧚 Fairy", "🧛 Vampire", "🐺 Werewolf"),
    "ru": ("👤 Человек", "🧝 Эльф", "😈 Демон", "⛏️ Дварф", "🐉 Драконит", "🧚 Фея", "🧛 Вампир", "🐺 Оборотень"),
}


def gender_keyboard(language: str = "fa") -> InlineKeyboardMarkup:
    male, female = _GENDER.get(language, _GENDER["fa"])
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=male, callback_data="gender:male"),
        InlineKeyboardButton(text=female, callback_data="gender:female"),
    ]])


def race_keyboard(language: str = "fa") -> InlineKeyboardMarkup:
    labels = _RACES.get(language, _RACES["fa"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=labels[0], callback_data="race:human"),
            InlineKeyboardButton(text=labels[1], callback_data="race:elf"),
        ],
        [
            InlineKeyboardButton(text=labels[2], callback_data="race:demon"),
            InlineKeyboardButton(text=labels[3], callback_data="race:dwarf"),
        ],
        [
            InlineKeyboardButton(text=labels[4], callback_data="race:dragonite"),
            InlineKeyboardButton(text=labels[5], callback_data="race:fairy"),
        ],
        [
            InlineKeyboardButton(text=labels[6], callback_data="race:vampire"),
            InlineKeyboardButton(text=labels[7], callback_data="race:werewolf"),
        ],
    ])
