from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InputMediaPhoto,
    Message,
)

from config.settings import settings
from middlewares.panel_owner import protect_keyboard
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
    sell_owned_fan_art,
)
from states.fan_art import FanArtStates
from database.redis import redis
from services.panel_image_service import replace_panel_with_photo, replace_panel_with_text, send_panel

FAN_ART_PANEL_TTL = 60 * 60 * 24 * 30


def _fan_art_panel_key(chat_id: int, owner_id: int) -> str:
    return f"eldoria:fanart_panel:{chat_id}:{owner_id}"


async def _replace_previous_fan_art_panel(
    callback: CallbackQuery,
    *,
    preserve_current: bool = False,
) -> None:
    """Delete this player's previous Fan Art panel, including the clicked panel."""
    message = callback.message
    if message is None:
        return
    key = _fan_art_panel_key(message.chat.id, callback.from_user.id)
    try:
        previous = await redis.get(key)
        if previous:
            try:
                previous_id = int(previous)
                # Navigation sends a new message, so even the clicked panel
                # must be removed. Payment instead edits the clicked panel.
                if not (preserve_current and previous_id == message.message_id):
                    await message.bot.delete_message(
                        chat_id=message.chat.id,
                        message_id=previous_id,
                    )
            except Exception:
                # The message may already be deleted or Telegram may reject deletion.
                pass
        await redis.delete(key)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Could not replace previous Fan Art panel")


async def _save_fan_art_panel(callback: CallbackQuery, message: Message) -> None:
    try:
        await redis.set(
            _fan_art_panel_key(message.chat.id, callback.from_user.id),
            str(message.message_id),
            ex=FAN_ART_PANEL_TTL,
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Could not save Fan Art panel reference")


async def _remove_active_shop_panel(chat_id: int, owner_id: int, bot) -> None:
    """Remove only this player's shop panel when they enter the Fan Art flow."""
    key = f"eldoria:active_panel:{chat_id}:{owner_id}:shop"
    try:
        previous = await redis.get(key)
        if previous:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=int(previous))
            except Exception:
                # The panel may already be gone or no longer deletable.
                pass
        await redis.delete(key)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Could not remove previous shop panel")


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
    """Edit the current panel; replace it only if it is currently a media message."""
    return await replace_panel_with_text(
        callback=callback,
        text=text,
        reply_markup=reply_markup,
        parse_mode="HTML",
    )


async def show_photo(
    callback: CallbackQuery,
    photo: str,
    caption: str,
    reply_markup=None,
):
    """Fan Art images replace the current panel instead of stacking new messages."""
    return await replace_panel_with_photo(
        callback=callback,
        photo=photo,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode="HTML",
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

    # One price drives both the real-currency price and the in-game value.
    real_price_toman = int(fan_art.price)
    game_price_gold = (real_price_toman * 2000) // 50000
    caption = (
        f"🎨 <b>{fan_art.name}</b> · {RARITY_NAMES.get(fan_art.rarity, fan_art.rarity)}\n"
        f"💰 {real_price_toman:,} تومان · 🪙 {game_price_gold:,} گلد"
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

    # Payment details reuse the clicked panel, so do not delete that message.
    await _replace_previous_fan_art_panel(callback, preserve_current=True)

    payment_info = settings.fanart_payment_info

    caption = (
        f"💳 پرداخت Fan Art\n\n"
        f"🎨 {fan_art.name}\n"
        f"💎 رریتی: "
        f"{RARITY_NAMES.get(fan_art.rarity, fan_art.rarity)}\n"
        f"💰 مبلغ: {int(fan_art.price):,}\n\n"
        f"📌 اطلاعات پرداخت:\n"
        f"{payment_info}\n\n"
        "پس از پرداخت، روی «💳 پرداخت کردم» بزن."
    )

    if callback.message.photo:
        await callback.message.edit_caption(
            caption=caption,
            reply_markup=protect_keyboard(
                fan_art_payment_keyboard(fan_art.id),
                callback.from_user.id,
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
                f"🎨 Fan Art: {active_order.fan_art.name}\n"
                f"📌 وضعیت: {status_text}\n\n"
                "جزئیات و شماره سفارش فقط در پی‌وی ربات نمایش داده می‌شود."
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

        # Keep the payment panel in chat history so the user can refer back to it.
        # The next receipt instructions are sent as a separate message.

        await callback.message.answer(
            "📷 ارسال رسید پرداخت\n\n"
            f"🎨 Fan Art: {order.fan_art.name}\n"
            f"💰 مبلغ: {int(order.price_snapshot):,}\n\n"
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

    receipt_confirmation = (
        "✅ رسید با موفقیت دریافت شد.\n\n"
        f"🆔 سفارش: {order.order_code}\n"
        f"🎨 Fan Art: {order.fan_art.name}\n\n"
        "رسید برای مدیریت ارسال شد.\n"
        "پس از بررسی، نتیجه به شما اعلام می‌شود."
    )

    if message.chat.type in {"group", "supergroup"} and message.from_user is not None:
        # Keep the order code and Fan Art name private to prevent impersonation
        # or fake-order claims in the group.
        private_sent = False
        try:
            await message.bot.send_message(
                chat_id=message.from_user.id,
                text=receipt_confirmation,
            )
            private_sent = True
        except Exception as exc:
            # The player may not have opened the bot privately yet.
            print("FAN ART PRIVATE CONFIRMATION ERROR:", repr(exc))

        if private_sent:
            await message.answer("✅ رسید دریافت شد؛ سریال سفارش شما در پی‌وی ربات ارسال شد.")
        else:
            await message.answer(
                "✅ رسید دریافت شد، اما ارسال پیام خصوصی ممکن نشد. "
                "لطفاً ابتدا پی‌وی ربات را باز کن و /start بزن؛ شماره سفارش در گروه نمایش داده نمی‌شود."
            )
    else:
        # In private chat, show the full order confirmation directly.
        await message.answer(receipt_confirmation)

    try:
        await message.bot.send_photo(
            chat_id=settings.admin_id,
            photo=receipt_file_id,
            caption=(
                "💳 رسید جدید Fan Art\n\n"
                f"🆔 سفارش: {order.order_code}\n"
                f"🎨 Fan Art: {order.fan_art.name}\n"
                f"💰 مبلغ: {int(order.price_snapshot):,}\n"
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
            "🗃 سفارش‌های من\n\n"
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
        "🗃 سفارش فعال\n\n"
        f"🆔 سفارش: {order.order_code}\n"
        f"🎨 Fan Art: {order.fan_art.name}\n"
        f"💰 مبلغ: {int(order.price_snapshot):,}\n"
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

@router.callback_query(F.data.startswith("fanart:sell:"))
async def fan_art_sell(callback: CallbackQuery):
    try:
        fan_art_id = int((callback.data or "").rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("شناسه فن‌آرت نامعتبر است.", show_alert=True); return
    success, message = await sell_owned_fan_art(callback.from_user.id, fan_art_id)
    await callback.answer(message[:180], show_alert=True)
    owned = await get_owned_fan_arts(callback.from_user.id)
    await show_text(callback, "🏆 <b>مجموعهٔ فن‌آرت‌های من</b>\n\n" + ("فن‌آرتی برای نمایش باقی نمانده است." if not owned else "برای انتخاب یا فروش فن‌آرت اقدام کن."), fan_art_owned_keyboard(owned) if owned else fan_art_main_keyboard())


@router.message(Command("arts", ignore_case=True))
@router.message(F.text.regexp(r"(?i)^\s*(ارت ها|ارت‌ها|فن.?آرت|فن.?آرت ها|فن.?آرت‌ها)\s*$"))
async def fan_art_text_entry(message: Message):
    """Open Fan Art as the player's current panel, replacing the previous menu."""
    await send_panel(
        message=message,
        panel_name="fan_art",
        text=(
            "🎨 <b>تالار فن‌آرت اِلدوریا</b>\n\n"
            "از این بخش می‌توانی فن‌آرت‌ها را مرور کنی؛ فن‌آرت‌های خودت را از صندوقچهٔ قهرمان ببین."
        ),
        reply_markup=fan_art_main_keyboard(),
        parse_mode="HTML",
    )