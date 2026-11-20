from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def equipment_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚔️ سلاح‌ها",
                    callback_data="equipment:list:weapon",
                ),
                InlineKeyboardButton(
                    text="🪖 کلاه‌ها",
                    callback_data="equipment:list:helmet",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🛡️ زره‌ها",
                    callback_data="equipment:list:armor",
                ),
                InlineKeyboardButton(
                    text="👢 کفش‌ها",
                    callback_data="equipment:list:boots",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💍 انگشترها",
                    callback_data="equipment:list:ring",
                ),
                InlineKeyboardButton(
                    text="📿 گردنبندها",
                    callback_data="equipment:list:necklace",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 آمار تجهیزات",
                    callback_data="equipment:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به منوی اصلی",
                    callback_data="equipment:back",
                ),
            ],
        ]
    )


def equipment_list_keyboard(
    equipment_items: list,
    equipment_type: str,
) -> InlineKeyboardMarkup:

    buttons = []

    for character_equipment, equipment in equipment_items:
        equipped_icon = "🟢 " if character_equipment.equipped else ""

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{equipped_icon}"
                        f"{equipment.name} "
                        f"×{character_equipment.quantity}"
                    ),
                    callback_data=f"equipment:item:{equipment.id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به تجهیزات",
                callback_data="equipment:menu",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def equipment_details_keyboard(
    equipment_id: int,
    equipped: bool,
    equipment_type: str,
) -> InlineKeyboardMarkup:

    if equipped:
        action_button = InlineKeyboardButton(
            text="❌ برداشتن تجهیز",
            callback_data=f"equipment:unequip:{equipment_id}",
        )
    else:
        action_button = InlineKeyboardButton(
            text="⚔️ تجهیز کردن",
            callback_data=f"equipment:equip:{equipment_id}",
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                action_button,
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به لیست",
                    callback_data=f"equipment:list:{equipment_type}",
                )
            ],
        ]
    )