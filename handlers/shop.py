from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


router = Router()


def shop_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎨 Fan Art",
                    callback_data="menu:fanart",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به منوی اصلی",
                    callback_data="menu:back",
                )
            ],
        ]
    )


@router.callback_query(
    F.data == "menu:shop"
)
async def shop_handler(
    callback: CallbackQuery,
):
    await callback.message.edit_text(
        "🛒 فروشگاه اِلدوریا\n\n"
        "محصولات ویژه و آیتم‌های قابل خرید را انتخاب کن:",
        reply_markup=shop_keyboard(),
    )

    await callback.answer()