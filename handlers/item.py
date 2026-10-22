from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


LABELS = {
    "fa": ("💰 فروش به فروشگاه", "👤 پیشنهاد به بازیکن", "🔙 بازگشت به صندوقچه", "✅ قبول معامله", "❌ رد معامله"),
    "en": ("💰 Sell to Shop", "👤 Offer to Player", "🔙 Back to Inventory", "✅ Accept Trade", "❌ Decline Trade"),
    "ru": ("💰 Продать магазину", "👤 Предложить игроку", "🔙 Назад в инвентарь", "✅ Принять обмен", "❌ Отклонить обмен"),
}


def _labels(language: str):
    return LABELS.get(language, LABELS["fa"])


def item_details_keyboard(item_id: int, language: str = "fa") -> InlineKeyboardMarkup:
    sell_shop, offer_player, back_inventory, _, _ = _labels(language)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=sell_shop, callback_data=f"item:sell:{item_id}"),
            InlineKeyboardButton(text=offer_player, callback_data=f"item:sell_player:{item_id}"),
        ],
        [InlineKeyboardButton(text=back_inventory, callback_data="menu:inventory")],
    ])


def trade_request_keyboard(trade_id: str, language: str = "fa") -> InlineKeyboardMarkup:
    _, _, _, accept, reject = _labels(language)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=accept, callback_data=f"trade:accept:{trade_id}"),
            InlineKeyboardButton(text=reject, callback_data=f"trade:reject:{trade_id}"),
        ],
    ])
