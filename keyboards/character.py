from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚔️ مرد", callback_data="gender:male"),
                InlineKeyboardButton(text="🌙 زن", callback_data="gender:female"),
            ]
        ]
    )


def race_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 انسان", callback_data="race:human"),
                InlineKeyboardButton(text="🧝 الف", callback_data="race:elf"),
            ],
            [
                InlineKeyboardButton(text="😈 شیطان", callback_data="race:demon"),
                InlineKeyboardButton(text="⛏️ دورف", callback_data="race:dwarf"),
            ],
            [
                InlineKeyboardButton(text="🐉 درگونایت", callback_data="race:dragonite"),
                InlineKeyboardButton(text="🧚 پری", callback_data="race:fairy"),
            ],
            [
                InlineKeyboardButton(text="🧛 خون‌آشام", callback_data="race:vampire"),
                InlineKeyboardButton(text="🐺 گرگینه", callback_data="race:werewolf"),
            ],
        ]
    )
