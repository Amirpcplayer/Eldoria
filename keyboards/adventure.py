from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def adventure_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌲 مناطق ماجراجویی",
                    callback_data="adventure:areas",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به منوی اصلی",
                    callback_data="adventure:back",
                )
            ],
        ]
    )


def adventure_areas_keyboard(
    areas: list,
) -> InlineKeyboardMarkup:
    buttons = []

    for area in areas:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=area.name,
                    callback_data=f"adventure:area:{area.id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به ماجراجویی",
                callback_data="adventure:menu",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def adventure_area_keyboard(
    area_id: int,
    unlocked: bool,
) -> InlineKeyboardMarkup:
    buttons = []

    if unlocked:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⚔️ ورود به منطقه",
                    callback_data=f"adventure:start:{area_id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به مناطق",
                callback_data="adventure:areas",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def adventure_encounter_keyboard(
    area_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚔️ انتخاب دشمن",
                    callback_data=f"adventure:enemies:{area_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به منطقه",
                    callback_data=f"adventure:area:{area_id}",
                )
            ],
        ]
    )


def adventure_enemies_keyboard(
    enemies: list,
    area_id: int,
) -> InlineKeyboardMarkup:
    buttons = []

    for enemy in enemies:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"👾 {enemy.name} • Lv.{enemy.level}",
                    callback_data=f"adventure:enemy:{enemy.id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به منطقه",
                callback_data=f"adventure:area:{area_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def adventure_enemy_keyboard(
    enemy_id: int,
    area_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚔️ آماده مبارزه",
                    callback_data=f"adventure:fight:{enemy_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به دشمنان",
                    callback_data=f"adventure:enemies:{area_id}",
                )
            ],
        ]
    )