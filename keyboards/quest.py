from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ============================================================
# Quest Main Menu
# ============================================================

def quest_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 داستانی",
                    callback_data="quest:list:story",
                ),
                InlineKeyboardButton(
                    text="📅 روزانه",
                    callback_data="quest:list:daily",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏆 دستاوردها",
                    callback_data="quest:list:achievement",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📌 مأموریت‌های من",
                    callback_data="quest:current_list",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="menu:back",
                ),
            ],
        ]
    )


# ============================================================
# Quest Category List
# ============================================================

def quest_list_keyboard(
    quests,
    category: str,
) -> InlineKeyboardMarkup:
    rows = []

    for character_quest, quest in quests:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📜 {quest.name}",
                    callback_data=f"quest:view:{quest.id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به مأموریت‌ها",
                callback_data="quest:menu",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# ============================================================
# Quest Detail
# ============================================================

def quest_detail_keyboard(
    quest_id: int,
    can_claim: bool,
) -> InlineKeyboardMarkup:
    rows = []

    if can_claim:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎁 دریافت جایزه",
                    callback_data=f"quest:claim:{quest_id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به مأموریت‌ها",
                callback_data="quest:menu",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# ============================================================
# My Quests
# ============================================================

def quest_current_list_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 داستانی",
                    callback_data="quest:list:story",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 روزانه",
                    callback_data="quest:list:daily",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 دستاوردها",
                    callback_data="quest:list:achievement",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به مأموریت‌ها",
                    callback_data="quest:menu",
                )
            ],
        ]
    )