from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.scroll_service import scroll_kind


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
                    text="🗃 متریال‌ها",
                    callback_data="inventory:materials",
                ),
                InlineKeyboardButton(
                    text="📜 اسکرول‌ها",
                    callback_data="inventory:scrolls",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📦 همه آیتم‌های موجود",
                    callback_data="inventory:all",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎨 فن‌آرت‌های من",
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


def inventory_items_keyboard(items) -> InlineKeyboardMarkup:
    rows = []

    for inventory_item, item in items:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{item.name} × {inventory_item.quantity}",
                    callback_data=f"item:{item.id}",
                )
            ]
        )
        # Scrolls can be read directly from the scroll list; the handler
        # validates ownership and enforces the two-hour effect cooldown.
        if scroll_kind(item.name):
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"📖 خواندن و فعال‌سازی: {item.name}",
                        callback_data=f"item:use_scroll:{item.id}",
                    )
                ]
            )

    if not rows:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📭 این بخش خالی است",
                    callback_data="inventory:noop",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به صندوقچه",
                callback_data="menu:inventory",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def equipment_items_keyboard(items) -> InlineKeyboardMarkup:
    rows = []

    for owned, equipment in items:
        equipped_mark = " ✅" if owned.equipped else ""

        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{equipment.name} × {owned.quantity}"
                        f"{equipped_mark}"
                    ),
                    callback_data=f"equipmentitem:{equipment.id}",
                )
            ]
        )

    if not rows:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📭 تجهیزاتی در صندوقچه نیست",
                    callback_data="inventory:noop",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به صندوقچه",
                callback_data="menu:inventory",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def equipment_item_details_keyboard(
    equipment_id: int,
    equipped: bool,
) -> InlineKeyboardMarkup:
    if equipped:
        action_button = InlineKeyboardButton(
            text="❌ برداشتن",
            callback_data=f"inventory:unequip:{equipment_id}",
        )
    else:
        action_button = InlineKeyboardButton(
            text="🗡️ استفاده",
            callback_data=f"inventory:equip:{equipment_id}",
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                action_button,
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به تجهیزات",
                    callback_data="inventory:equipment",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗃 بازگشت به صندوقچه",
                    callback_data="menu:inventory",
                )
            ],
        ]
    )


def fan_art_inventory_keyboard(fan_arts) -> InlineKeyboardMarkup:
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

    if not rows:
        rows.append(
            [
                InlineKeyboardButton(
                    text="📭 هنوز Fan Art ندارید",
                    callback_data="inventory:noop",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به صندوقچه",
                callback_data="menu:inventory",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)