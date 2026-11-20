from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def pvp_request_keyboard(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ قبول مبارزه",
                    callback_data=f"pvp:accept:{request_id}",
                ),
                InlineKeyboardButton(
                    text="❌ رد درخواست",
                    callback_data=f"pvp:decline:{request_id}",
                ),
            ]
        ]
    )


def pvp_battle_keyboard(battle_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚔️ حمله",
                    callback_data=f"pvp:action:{battle_id}:attack",
                ),
                InlineKeyboardButton(
                    text="🔮 مهارت‌ها",
                    callback_data=f"pvp:skills:{battle_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🧪 معجون / درمان",
                    callback_data=f"pvp:potions:{battle_id}",
                ),
                InlineKeyboardButton(
                    text="🏳️ تسلیم",
                    callback_data=f"pvp:action:{battle_id}:flee",
                ),
            ],
        ]
    )


def pvp_skills_keyboard(
    battle_id: str,
    skills: list,
) -> InlineKeyboardMarkup:
    rows = []

    for skill, character_skill in skills:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🔮 {skill.name} (Lv.{character_skill.level})",
                    callback_data=f"pvp:skill:{battle_id}:{skill.id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data=f"pvp:back:{battle_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def pvp_potions_keyboard(
    battle_id: str,
    potions: list[tuple[int, str, int, int]],
) -> InlineKeyboardMarkup:
    rows = []

    for item_id, item_name, quantity, heal_amount in potions:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{item_name} ×{quantity} (+{heal_amount} HP)",
                    callback_data=f"pvp:potion:{battle_id}:{item_id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به مبارزه",
                callback_data=f"pvp:back:{battle_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)