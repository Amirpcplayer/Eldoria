from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


RARITIES = [
    ("common", "⚪ Common"),
    ("rare", "🔵 Rare"),
    ("epic", "🟣 Epic"),
    ("legendary", "🟠 Legendary"),
    ("mythic", "🔴 Mythic"),
]


def fan_art_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎨 مشاهده Fan Artها",
                    callback_data="fanart:rarities",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 Fan Artهای من",
                    callback_data="fanart:owned",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗃 سفارش‌های من",
                    callback_data="fanart:orders",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به فروشگاه",
                    callback_data="menu:shop",
                )
            ],
        ]
    )


def fan_art_rarities_keyboard() -> InlineKeyboardMarkup:
    rows = []

    for rarity_id, rarity_name in RARITIES:
        rows.append(
            [
                InlineKeyboardButton(
                    text=rarity_name,
                    callback_data=f"fanart:rarity:{rarity_id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="menu:fanart",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def fan_art_list_keyboard(
    fan_arts,
) -> InlineKeyboardMarkup:
    rows = []

    for fan_art in fan_arts:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🎨 {fan_art.name}",
                    callback_data=f"fanart:view:{fan_art.id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="fanart:rarities",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def fan_art_detail_keyboard(
    fan_art_id: int,
    owned: bool = False,
) -> InlineKeyboardMarkup:
    rows = []

    if owned:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ در صندوقچه شماست",
                    callback_data="fanart:noop",
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💳 خرید Fan Art",
                    callback_data=f"fanart:buy:{fan_art_id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="fanart:rarities",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def fan_art_payment_keyboard(
    fan_art_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 پرداخت کردم",
                    callback_data=f"fanart:paid:{fan_art_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ نمی‌خواهم",
                    callback_data="fanart:cancel",
                )
            ],
        ]
    )


def fan_art_receipt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ لغو سفارش",
                    callback_data="fanart:cancel",
                )
            ]
        ]
    )


def fan_art_owned_keyboard(fan_arts) -> InlineKeyboardMarkup:
    rows = []
    for fan_art in fan_arts:
        rows.append([InlineKeyboardButton(text=f"🎨 {fan_art.name}", callback_data=f"fanart:select:{fan_art.id}")])
        value = int(getattr(fan_art, "value_gold", 0) or 0)
        if value > 0:
            rows.append([InlineKeyboardButton(text=f"💰 فروش برای {value:,} طلا", callback_data=f"fanart:sell:{fan_art.id}")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:fanart")])
    return InlineKeyboardMarkup(inline_keyboard=rows)



def fan_art_admin_order_keyboard(
    order_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید سفارش",
                    callback_data=f"fanartadmin:approve:{order_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ رد سفارش",
                    callback_data=f"fanartadmin:reject:{order_id}",
                )
            ],
        ]
    )