from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InputMediaPhoto,
    Message,
)

from config.settings import settings
from keyboards.fan_art import (
    fan_art_admin_order_keyboard,
    fan_art_detail_keyboard,
    fan_art_list_keyboard,
    fan_art_main_keyboard,
    fan_art_owned_keyboard,
    fan_art_payment_keyboard,
    fan_art_rarities_keyboard,
)
from services.fan_art_service import (
    PENDING_PAYMENT,
    WAITING_RECEIPT,
    attach_receipt,
    cancel_active_order,
    create_order,
    get_active_fan_arts,
    get_active_order,
    get_fan_art,
    get_owned_fan_arts,
    owns_fan_art,
    set_waiting_receipt,
)
from states.fan_art import FanArtStates


router = Router()


RARITY_NAMES = {
    "common": "⚪ Common",
    "rare": "🔵 Rare",
    "epic": "🟣 Epic",
    "legendary": "🟠 Legendary",
    "mythic": "🔴 Mythic",
}


async def show_text(
    callback: CallbackQuery,
    text: str,
    reply_markup=None,
):
    if callback.message.photo:
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            text,
            reply_markup=reply_markup,
        )
        return

    await callback.message.edit_text(
        text,
        reply_markup=reply_markup,
    )


async def show_photo(
    callback: CallbackQuery,
    photo: str,
    caption: str,
    reply_markup=None,
):
    if callback.message.photo:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=photo,
                caption=caption,
            ),
            reply_markup=reply_markup,
        )
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=reply_markup,
    )


@router.callback_query(F.data == "menu:fanart")
async def fan_art_main(
    callback: CallbackQuery,
):
    await callback.answer()

    await show_text(
        callback,
        "🎨 Fan Art اِلدوریا\n\n"
        "فن‌آرت‌های ویژه را از فروشگاه انتخاب کن.\n"
        "فن‌آرت خریداری‌شده به صندوقچه شما اضافه می‌شود.",
        fan_art_main_keyboard(),
    )


@router.callback_query(F.data == "fanart:rarities")
async def fan_art_rarities(
    callback: CallbackQuery,
):
    await callback.answer()

    await show_text(
        callback,
        "💎 رریتی Fan Art را انتخاب کن:",
        fan_art_rarities_keyboard(),
    )


@router.callback_query(F.data.startswith("fanart:rarity:"))
async def fan_art_rarity(
    callback: CallbackQuery,
):
    await callback.answer()

    rarity = callback.data.split(":")[-1]

    fan_arts = await get_active_fan_arts()

    fan_arts = [
        fan_art
        for fan_art in fan_arts
        if fan_art.rarity == rarity
    ]

    rarity_name = RARITY_NAMES.get(
        rarity,
        rarity,
    )

    if not fan_arts:
        await show_text(
            callback,
            f"{rarity_name}\n\n"
            "فعلاً Fan Artای در این رریتی موجود نیست.",
            fan_art_rarities_keyboard(),
        )
        return

    await show_text(
        callback,
        f"{rarity_name}\n\n"
        "Fan Art موردنظر را انتخاب کن:",
        fan_art_list_keyboard(fan_arts),
    )


@router.callback_query(F.data.startswith("fanart:view:"))
async def fan_art_view(
    callback: CallbackQuery,
):
    try:
        fan_art_id = int(
            callback.data.split(":")[-1]
        )
    except ValueError:
        await callback.answer(
            "شناسه Fan Art نامعتبر است.",
            show_alert=True,
        )
        return

    fan_art = await get_fan_art(
        fan_art_id,
    )

    if fan_art is None or not fan_art.is_active:
        await callback.answer(
            "این Fan Art دیگر موجود نیست.",
            show_alert=True,
        )
        return

    owned = await owns_fan_art(
        callback.from_user.id,
        fan_art.id,
    )

    rarity_name = RARITY_NAMES.get(
        fan_art.rarity,
        fan_art.rarity,
    )

    if fan_art.is_limited:
        stock_text = (
            f"📦 موجودی: {fan_art.stock or 0}"
        )
    else:
        stock_text = "📦 موجودی: نامحدود"

    caption = (
        f"🎨 {fan_art.name}\n\n"
        f"{fan_art.description}\n\n"
        f"💎 رریتی: {rarity_name}\n"
        f"💰 قیمت: {fan_art.price}\n"
        f"{stock_text}"
    )

    await show_photo(
        callback,
        fan_art.image_file_id,
        caption,
        fan_art_detail_keyboard(
            fan_art.id,
            owned=owned,
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("fanart:buy:"))
async def fan_art_buy(
    callback: CallbackQuery,
):
    try:
        fan_art_id = int(
            callback.data.split(":")[-1]
        )
    except ValueError:
        await callback.answer(
            "شناسه Fan Art نامعتبر است.",
            show_alert=True,
        )
        return

    fan_art = await get_fan_art(
        fan_art_id,
    )

    if fan_art is None or not fan_art.is_active:
        await callback.answer(
            "این Fan Art موجود نیست.",
            show_alert=True,
        )
        return

    if await owns_fan_art(
        callback.from_user.id,
        fan_art.id,
    ):
        await callback.answer(
            "این Fan Art را قبلاً خریداری کرده‌ای.",
            show_alert=True,
        )
        return

    if fan_art.is_limited:
        if fan_art.stock is None or fan_art.stock <= 0:
            await callback.answer(
                "موجودی این Fan Art تمام شده است.",
                show_alert=True,
            )
            return

    active_order = await get_active_order(
        callback.from_user.id,
    )

    if active_order is not None:
        await callback.answer(
            "شما یک سفارش فعال دارید. ابتدا همان سفارش را تکمیل یا لغو کن.",
            show_alert=True,
        )
        return

    payment_info = settings.fanart_payment_info

    caption = (
        f"💳 پرداخت Fan Art\n\n"
        f"🎨 {fan_art.name}\n"
        f"💎 رریتی: "
        f"{RARITY_NAMES.get(fan_art.rarity, fan_art.rarity)}\n"
        f"💰 مبلغ: {fan_art.price}\n\n"
        f"📌 اطلاعات پرداخت:\n"
        f"{payment_info}\n\n"
        "پس از پرداخت، روی «💳 پرداخت کردم» بزن."
    )

    if callback.message.photo:
        await callback.message.edit_caption(
            caption=caption,
            reply_markup=fan_art_payment_keyboard(
                fan_art.id,
            ),
        )
    else:
        await callback.message.edit_text(
            caption,
            reply_markup=fan_art_payment_keyboard(
                fan_art.id,
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("fanart:paid:"))
async def fan_art_paid(
    callback: CallbackQuery,
    state: FSMContext,
):
    """
    Starts the real Fan Art order flow.

    Important:
    We answer the Telegram callback immediately so the button
    never appears frozen while database operations are running.
    """

    await callback.answer(
        "⏳ در حال ثبت سفارش..."
    )

    try:
        fan_art_id = int(
            callback.data.split(":")[-1]
        )
    except (ValueError, AttributeError):
        await callback.message.answer(
            "❌ شناسه Fan Art نامعتبر است."
        )
        return

    try:
        fan_art = await get_fan_art(
            fan_art_id,
        )

        if fan_art is None or not fan_art.is_active:
            await callback.message.answer(
                "❌ این Fan Art دیگر موجود نیست."
            )
            return

        if await owns_fan_art(
            callback.from_user.id,
            fan_art.id,
        ):
            await callback.message.answer(
                "⚠️ این Fan Art را قبلاً خریداری کرده‌ای."
            )
            return

        active_order = await get_active_order(
            callback.from_user.id,
        )

        if active_order is not None:
            status_names = {
                PENDING_PAYMENT: "⏳ منتظر پرداخت",
                WAITING_RECEIPT: "📷 منتظر رسید",
                "UNDER_REVIEW": "🔎 در حال بررسی",
            }

            status_text = status_names.get(
                active_order.status,
                active_order.status,
            )

            await callback.message.answer(
                "⚠️ شما یک سفارش فعال دارید.\n\n"
                f"🆔 سفارش: {active_order.order_code}\n"
                f"🎨 Fan Art: {active_order.fan_art.name}\n"
                f"📌 وضعیت: {status_text}"
            )
            return

        order = await create_order(
            telegram_id=callback.from_user.id,
            fan_art_id=fan_art_id,
        )

        if order is None:
            await callback.message.answer(
                "❌ ایجاد سفارش ناموفق بود."
            )
            return

        order = await set_waiting_receipt(
            order_id=order.id,
            telegram_id=callback.from_user.id,
        )

        if order is None:
            await callback.message.answer(
                "❌ سفارش ایجاد شد اما انتقال آن به مرحله دریافت رسید ناموفق بود."
            )
            return

        await state.clear()

        await state.update_data(
            order_id=order.id,
            fan_art_id=fan_art_id,
        )

        await state.set_state(
            FanArtStates.waiting_receipt,
        )

        try:
            if callback.message.photo:
                await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            "📷 ارسال رسید پرداخت\n\n"
            f"🆔 شماره سفارش: {order.order_code}\n"
            f"🎨 Fan Art: {order.fan_art.name}\n"
            f"💰 مبلغ: {order.price_snapshot}\n\n"
            "حالا تصویر رسید پرداخت را به صورت Photo ارسال کن.",
            reply_markup=None,
        )

    except ValueError as exc:
        error = str(exc)

        messages = {
            "ACTIVE_ORDER_EXISTS": (
                "⚠️ شما یک سفارش فعال دارید."
            ),
            "FAN_ART_NOT_FOUND": (
                "❌ این Fan Art موجود نیست."
            ),
            "OUT_OF_STOCK": (
                "❌ موجودی این Fan Art تمام شده است."
            ),
            "ALREADY_OWNED": (
                "⚠️ این Fan Art را قبلاً خریداری کرده‌ای."
            ),
        }

        await state.clear()

        await callback.message.answer(
            messages.get(
                error,
                f"❌ خطا در ایجاد سفارش: {error}",
            )
        )

    except Exception as exc:
        await state.clear()

        print(
            "FAN ART PAYMENT ERROR:",
            repr(exc),
        )

        await callback.message.answer(
            "❌ هنگام ثبت سفارش یک خطای غیرمنتظره رخ داد.\n\n"
            "لطفاً دوباره تلاش کن."
        )


@router.message(
    FanArtStates.waiting_receipt,
    F.photo,
)
async def fan_art_receipt(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    order_id = data.get(
        "order_id"
    )

    if not order_id:
        await state.clear()

        await message.answer(
            "❌ سفارش پیدا نشد."
        )
        return

    receipt_file_id = message.photo[-1].file_id

    try:
        order = await attach_receipt(
            order_id=order_id,
            telegram_id=message.from_user.id,
            receipt_file_id=receipt_file_id,
        )
    except Exception as exc:
        print(
            "FAN ART RECEIPT ERROR:",
            repr(exc),
        )

        await message.answer(
            "❌ هنگام ثبت رسید خطایی رخ داد.\n"
            "لطفاً دوباره تلاش کن."
        )
        return

    if order is None:
        await state.clear()

        await message.answer(
            "❌ این سفارش دیگر منتظر رسید نیست."
        )
        return

    await state.clear()

    await message.answer(
        "✅ رسید با موفقیت دریافت شد.\n\n"
        f"🆔 سفارش: {order.order_code}\n"
        f"🎨 Fan Art: {order.fan_art.name}\n\n"
        "رسید برای مدیریت ارسال شد.\n"
        "پس از بررسی، نتیجه به شما اعلام می‌شود."
    )

    try:
        await message.bot.send_photo(
            chat_id=settings.admin_id,
            photo=receipt_file_id,
            caption=(
                "💳 رسید جدید Fan Art\n\n"
                f"🆔 سفارش: {order.order_code}\n"
                f"🎨 Fan Art: {order.fan_art.name}\n"
                f"💰 مبلغ: {order.price_snapshot}\n"
                f"👤 Telegram ID: {order.telegram_id}\n"
                f"📌 وضعیت: {order.status}"
            ),
            reply_markup=fan_art_admin_order_keyboard(
                order.id,
            ),
        )
    except Exception as exc:
        print(
            "FAN ART ADMIN NOTIFICATION ERROR:",
            repr(exc),
        )


@router.message(
    FanArtStates.waiting_receipt,
)
async def fan_art_receipt_invalid(
    message: Message,
):
    await message.answer(
        "❌ لطفاً رسید را به صورت تصویر ارسال کن."
    )


@router.callback_query(
    F.data == "fanart:cancel"
)
async def fan_art_cancel(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer(
        "⏳ در حال لغو سفارش..."
    )

    try:
        cancelled = await cancel_active_order(
            callback.from_user.id,
        )
    except Exception as exc:
        print(
            "FAN ART CANCEL ERROR:",
            repr(exc),
        )

        await state.clear()

        await callback.message.answer(
            "❌ هنگام لغو سفارش خطایی رخ داد."
        )
        return

    await state.clear()

    if cancelled:
        text = "❌ سفارش لغو شد."
    else:
        text = "❌ سفارش فعالی پیدا نشد."

    await show_text(
        callback,
        text,
        fan_art_main_keyboard(),
    )


@router.callback_query(
    F.data == "fanart:owned"
)
async def fan_art_owned(
    callback: CallbackQuery,
):
    await callback.answer()

    owned = await get_owned_fan_arts(
        callback.from_user.id,
    )

    if not owned:
        await show_text(
            callback,
            "🏆 Fan Artهای من\n\n"
            "هنوز Fan Artای خریداری نکرده‌ای.",
            fan_art_main_keyboard(),
        )
        return

    await show_text(
        callback,
        "🏆 Fan Artهای من\n\n"
        "Fan Art موردنظر را انتخاب کن:",
        fan_art_owned_keyboard(
            owned,
        ),
    )


@router.callback_query(
    F.data.startswith("fanart:select:")
)
async def fan_art_select(
    callback: CallbackQuery,
):
    try:
        fan_art_id = int(
            callback.data.split(":")[-1]
        )
    except ValueError:
        await callback.answer(
            "شناسه نامعتبر است.",
            show_alert=True,
        )
        return

    if not await owns_fan_art(
        callback.from_user.id,
        fan_art_id,
    ):
        await callback.answer(
            "این Fan Art متعلق به شما نیست.",
            show_alert=True,
        )
        return

    await callback.answer(
        "انتخاب Fan Art برای پروفایل در بخش تنظیمات فعال می‌شود.",
        show_alert=True,
    )


@router.callback_query(
    F.data == "fanart:orders"
)
async def fan_art_orders(
    callback: CallbackQuery,
):
    await callback.answer()

    order = await get_active_order(
        callback.from_user.id,
    )

    if order is None:
        await show_text(
            callback,
            "📦 سفارش‌های من\n\n"
            "سفارش فعالی ندارید.",
            fan_art_main_keyboard(),
        )
        return

    status_names = {
        PENDING_PAYMENT: "⏳ منتظر پرداخت",
        WAITING_RECEIPT: "📷 منتظر رسید",
        "UNDER_REVIEW": "🔎 در حال بررسی",
    }

    status = status_names.get(
        order.status,
        order.status,
    )

    await show_text(
        callback,
        "📦 سفارش فعال\n\n"
        f"🆔 سفارش: {order.order_code}\n"
        f"🎨 Fan Art: {order.fan_art.name}\n"
        f"💰 مبلغ: {order.price_snapshot}\n"
        f"📌 وضعیت: {status}",
        fan_art_main_keyboard(),
    )


@router.callback_query(
    F.data == "fanart:noop"
)
async def fan_art_noop(
    callback: CallbackQuery,
):
    await callback.answer(
        "این Fan Art در صندوقچه شما قرار دارد.",
        show_alert=True,
    )