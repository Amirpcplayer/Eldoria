from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def inventory_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚔️ تجهیزات",
                    callback_data="inventory:equipment",
                ),
                InlineKeyboardButton(
                    text="🧪 معجون‌ها",
                    callback_data="inventory:potions",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📦 متریال",
                    callback_data="inventory:materials",
                ),
                InlineKeyboardButton(
                    text="📜 اسکرول‌ها",
                    callback_data="inventory:scrolls",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎨 Fan Art",
                    callback_data="inventory:fanart",
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


def inventory_items_keyboard(
    items,
) -> InlineKeyboardMarkup:

    buttons = []

    for inventory_item, item in items:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{item.name} × {inventory_item.quantity}",
                    callback_data=f"item:{item.id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به صندوقچه",
                callback_data="menu:inventory",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )