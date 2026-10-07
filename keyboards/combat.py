from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ============================================================
# MAIN COMBAT KEYBOARD
# ============================================================

def combat_keyboard(
    battle_id: str,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚔️ حمله",
                    callback_data=f"combat:attack:{battle_id}",
                ),
                InlineKeyboardButton(
                    text="🔮 مهارت‌ها",
                    callback_data=f"combat:skills:{battle_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🧪 معجون",
                    callback_data=f"combat:potions:{battle_id}",
                ),
                InlineKeyboardButton(
                    text="🏃 فرار",
                    callback_data=f"combat:flee:{battle_id}",
                ),
            ],
        ]
    )


# ============================================================
# HEALING POTIONS
# ============================================================

def combat_potions_keyboard(
    battle_id: str,
    potions: list,
) -> InlineKeyboardMarkup:

    buttons = []

    for inventory_item, item, heal_amount in potions:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{item.name} × {inventory_item.quantity}"
                        f" (+{heal_amount} HP)"
                    ),
                    callback_data=(
                        f"combat:potion:"
                        f"{battle_id}:"
                        f"{item.id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به مبارزه",
                callback_data=f"combat:back:{battle_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# ============================================================
# SKILLS
# ============================================================

def combat_skills_keyboard(
    battle_id: str,
    skills: list,
) -> InlineKeyboardMarkup:

    buttons = []

    for skill, character_skill in skills:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"🔮 {skill.name} "
                        f"(Lv.{character_skill.level})"
                    ),
                    callback_data=(
                        f"combat:skill:"
                        f"{battle_id}:"
                        f"{skill.id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به مبارزه",
                callback_data=f"combat:back:{battle_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# ============================================================
# SINGLE SKILL
# ============================================================

def combat_skill_keyboard(
    battle_id: str,
    skill_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ استفاده از مهارت",
                    callback_data=(
                        f"combat:skill:"
                        f"{battle_id}:"
                        f"{skill_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به مهارت‌ها",
                    callback_data=(
                        f"combat:skills:{battle_id}"
                    ),
                )
            ],
        ]
    )


# ============================================================
# RESULT
# ============================================================

def combat_result_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗺️ بازگشت به ماجراجویی",
                    callback_data="menu:adventure",
                )
            ]
        ]
    )


# ============================================================
# COMPATIBILITY
# ============================================================

def combat_main_keyboard(
    battle_id: str,
) -> InlineKeyboardMarkup:

    return combat_keyboard(
        battle_id
    )