from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def shop_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚔️ تجهیزات",
                    callback_data="shop:equipment",
                ),
                InlineKeyboardButton(
                    text="🧪 معجون‌ها",
                    callback_data="shop:potion",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗃 متریال",
                    callback_data="shop:material",
                ),
                InlineKeyboardButton(
                    text="📜 اسکرول‌ها",
                    callback_data="shop:scroll",
                ),
            ],
            [
                InlineKeyboardButton(text="💎 فروشگاه ویژهٔ جم", callback_data="shop:gems"),
            ],
            [
                InlineKeyboardButton(
                    text="🎨 Fan Art",
                    callback_data="menu:fanart",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="menu:back",
                )
            ],
        ]
    )


def shop_items_keyboard(
    items,
    item_type: str,
) -> InlineKeyboardMarkup:
    buttons = []

    for item in items:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{item.name} — 💰 {item.buy_price:,}",
                    callback_data=f"shop:item:{item.id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به فروشگاه",
                callback_data="menu:shop",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def shop_item_details_keyboard(item_id: int) -> InlineKeyboardMarkup:
    quantities = (1, 5, 10, 15, 20)
    rows = [[InlineKeyboardButton(text=f"🛒 خرید ×{qty}", callback_data=f"shop:buyqty:{item_id}:{qty}") for qty in quantities[:3]],
            [InlineKeyboardButton(text=f"🛒 خرید ×{qty}", callback_data=f"shop:buyqty:{item_id}:{qty}") for qty in quantities[3:]]]
    rows.extend([
        [InlineKeyboardButton(text="🔙 بازگشت به لیست", callback_data="shop:itemlist"), InlineKeyboardButton(text="🏪 فروشگاه", callback_data="menu:shop")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def shop_equipment_keyboard(
    equipment_list,
) -> InlineKeyboardMarkup:
    buttons = []

    for equipment in equipment_list:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{equipment.name} — "
                        f"💰 {equipment.shop_price:,}"
                    ),
                    callback_data=f"shop:equipment_item:{equipment.id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به فروشگاه",
                callback_data="menu:shop",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def shop_equipment_details_keyboard(
    equipment_id: int,
    can_buy: bool,
) -> InlineKeyboardMarkup:
    buttons = []

    if can_buy:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🛒 خرید تجهیزات",
                    callback_data=f"shop:buy_equipment:{equipment_id}",
                )
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به تجهیزات",
                    callback_data="shop:equipment",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏪 فروشگاه",
                    callback_data="menu:shop",
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
