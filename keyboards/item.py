from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def item_details_keyboard(
    item_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 فروش به فروشگاه",
                    callback_data=f"item:sell:{item_id}",
                ),
                InlineKeyboardButton(
                    text="👤 فروش به بازیکن",
                    callback_data=f"item:sell_player:{item_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به صندوقچه",
                    callback_data="menu:inventory",
                )
            ],
        ]
    )


def trade_request_keyboard(
    trade_id: str,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ قبول معامله",
                    callback_data=f"trade:accept:{trade_id}",
                ),
                InlineKeyboardButton(
                    text="❌ رد معامله",
                    callback_data=f"trade:reject:{trade_id}",
                ),
            ]
        ]
    )