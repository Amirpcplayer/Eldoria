from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.start_premium_emoji_service import get_start_emoji_ids

_GENDER = {
    "fa": ("مرد", "زن"),
    "en": ("Male", "Female"),
    "ru": ("Мужчина", "Женщина"),
}
_GENDER_ICONS = (("gender_male_button", "⚔️"), ("gender_female_button", "🌙"))

_RACES = {
    "fa": ("انسان", "الف", "شیطان", "دورف", "پری", "درگونایت", "گرگینه", "خون‌آشام"),
    "en": ("Human", "Elf", "Demon", "Dwarf", "Fairy", "Dragonkin", "Werewolf", "Vampire"),
    "ru": ("Человек", "Эльф", "Демон", "Дварф", "Фея", "Драконит", "Оборотень", "Вампир"),
}
_RACE_ICONS = (
    ("race_human_button", "👤", "human"),
    ("race_elf_button", "🧝", "elf"),
    ("race_demon_button", "😈", "demon"),
    ("race_dwarf_button", "⛏️", "dwarf"),
    ("race_fairy_button", "🧚", "fairy"),
    ("race_dragonite_button", "🐉", "dragonite"),
    ("race_werewolf_button", "🐺", "werewolf"),
    ("race_vampire_button", "🧛", "vampire"),
)


def gender_keyboard(language: str = "fa") -> InlineKeyboardMarkup:
    lang = language if language in _GENDER else "fa"
    labels = _GENDER[lang]
    ids = get_start_emoji_ids()
    buttons = []
    for index, (key, fallback) in enumerate(_GENDER_ICONS):
        custom_id = ids.get(key)
        buttons.append(InlineKeyboardButton(
            text=labels[index] if custom_id else f"{fallback} {labels[index]}",
            callback_data=("gender:male", "gender:female")[index],
            icon_custom_emoji_id=custom_id,
        ))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def race_keyboard(language: str = "fa") -> InlineKeyboardMarkup:
    lang = language if language in _RACES else "fa"
    labels = _RACES[lang]
    ids = get_start_emoji_ids()
    buttons = []
    for index, (key, fallback, race_id) in enumerate(_RACE_ICONS):
        custom_id = ids.get(key)
        buttons.append(InlineKeyboardButton(
            text=labels[index] if custom_id else f"{fallback} {labels[index]}",
            callback_data=f"race:{race_id}",
            icon_custom_emoji_id=custom_id,
        ))
    return InlineKeyboardMarkup(inline_keyboard=[
        buttons[0:2], buttons[2:4], buttons[4:6], buttons[6:8]
    ])
