from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config.settings import settings
from database.database import AsyncSessionLocal
from models.fan_art import FanArt
from services.fan_art_service import (
    APPROVED,
    approve_order,
    reject_order,
)
from states.fan_art import FanArtAdminStates, FanArtStates


router = Router()


RARITY_ALIASES = {
    "common": "common",
    "کامون": "common",
    "معمولی": "common",

    "rare": "rare",
    "کمیاب": "rare",

    "epic": "epic",
    "اپیک": "epic",

    "legendary": "legendary",
    "لجندری": "legendary",
    "افسانه‌ای": "legendary",
    "افسانه ای": "legendary",

    "mythic": "mythic",
    "میتیک": "mythic",
    "اسطوره‌ای": "mythic",
    "اسطوره ای": "mythic",
}


def is_admin(telegram_id: int) -> bool:
    return telegram_id == settings.admin_id


@router.message(Command("fanart_add"))
async def fanart_add_start(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    await state.set_state(FanArtStates.add_image)

    await message.answer(
        "🎨 افزودن Fan Art\n\n"
        "📷 تصویر Fan Art را ارسال کن.\n\n"
        "برای لغو: /cancel"
    )


@router.message(Command("cancel"))
async def fanart_cancel(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    current_state = await state.get_state()

    if current_state is None:
        return

    await state.clear()

    await message.answer(
        "❌ عملیات لغو شد."
    )


@router.message(
    FanArtStates.add_image,
    F.photo,
)
async def fanart_add_image(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(
        image_file_id=message.photo[-1].file_id,
    )

    await state.set_state(
        FanArtStates.add_name,
    )

    await message.answer(
        "📝 نام Fan Art را ارسال کن."
    )


@router.message(FanArtStates.add_image)
async def fanart_add_image_invalid(
    message: Message,
):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "❌ لطفاً تصویر Fan Art را به صورت Photo ارسال کن."
    )


@router.message(
    FanArtStates.add_name,
    F.text,
)
async def fanart_add_name(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    name = message.text.strip()

    if not name:
        await message.answer(
            "❌ نام نمی‌تواند خالی باشد."
        )
        return

    if len(name) > 150:
        await message.answer(
            "❌ نام نباید بیشتر از ۱۵۰ قهرمان باشد."
        )
        return

    await state.update_data(
        name=name,
    )

    await state.set_state(
        FanArtStates.add_description,
    )

    await message.answer(
        "📖 توضیحات Fan Art را ارسال کن."
    )


@router.message(
    FanArtStates.add_description,
    F.text,
)
async def fanart_add_description(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    description = message.text.strip()

    if not description:
        await message.answer(
            "❌ توضیحات نمی‌تواند خالی باشد."
        )
        return

    await state.update_data(
        description=description,
    )

    await state.set_state(
        FanArtStates.add_rarity,
    )

    await message.answer(
        "💎 رریتی Fan Art را ارسال کن.\n\n"
        "گزینه‌ها:\n"
        "common\n"
        "rare\n"
        "epic\n"
        "legendary\n"
        "mythic"
    )


@router.message(
    FanArtStates.add_rarity,
    F.text,
)
async def fanart_add_rarity(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip().lower()
    rarity = RARITY_ALIASES.get(value)

    if rarity is None:
        await message.answer(
            "❌ رریتی نامعتبر است.\n\n"
            "common\n"
            "rare\n"
            "epic\n"
            "legendary\n"
            "mythic"
        )
        return

    await state.update_data(
        rarity=rarity,
    )

    await state.set_state(
        FanArtStates.add_price,
    )

    await message.answer(
        "💰 قیمت Fan Art را به صورت عددی وارد کن.\n\n"
        "مثال:\n"
        "250000"
    )


@router.message(
    FanArtStates.add_price,
    F.text,
)
async def fanart_add_price(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    raw_price = (
        message.text
        .strip()
        .replace(",", "")
        .replace("٬", "")
    )

    try:
        price = Decimal(raw_price)
    except InvalidOperation:
        await message.answer(
            "❌ قیمت نامعتبر است."
        )
        return

    if price <= 0:
        await message.answer(
            "❌ قیمت باید بیشتر از صفر باشد."
        )
        return

    await state.update_data(price=price)
    await state.set_state(FanArtStates.add_value_gold)
    await message.answer(
        "💰 ارزش اقتصادی این فن‌آرت در بازی را به طلا وارد کن.\n"
        "این مقدار با قیمت پرداختی جداست و در شکار/اقتصاد بازی نمایش داده می‌شود.\n\n"
        "مثال: 25000"
    )

@router.message(FanArtStates.add_value_gold, F.text)
async def fanart_add_value_gold(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    raw = message.text.strip().replace(",", "").replace("٬", "")
    try:
        value_gold = int(raw)
    except ValueError:
        await message.answer("❌ ارزش اقتصادی باید عدد صحیح باشد.")
        return
    if value_gold < 0 or value_gold > 2_000_000_000:
        await message.answer("❌ ارزش اقتصادی باید بین صفر تا ۲٬۰۰۰٬۰۰۰٬۰۰۰ طلا باشد.")
        return
    await state.update_data(value_gold=value_gold)
    await state.set_state(FanArtStates.add_limited)
    await message.answer("🗃 آیا Fan Art محدود است؟\n\nبله\nیا\nخیر")


@router.message(
    FanArtStates.add_limited,
    F.text,
)
async def fanart_add_limited(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip().lower()

    if value in {
        "بله",
        "yes",
        "y",
    }:
        await state.update_data(
            is_limited=True,
        )

        await state.set_state(
            FanArtStates.add_stock,
        )

        await message.answer(
            "🗃 تعداد موجودی را وارد کن.\n\n"
            "مثال:\n"
            "10"
        )

        return

    if value in {
        "خیر",
        "نه",
        "no",
        "n",
    }:
        await state.update_data(
            is_limited=False,
            stock=None,
        )

        await create_fan_art(
            message,
            state,
        )

        return

    await message.answer(
        "❌ فقط «بله» یا «خیر» ارسال کن."
    )


@router.message(
    FanArtStates.add_stock,
    F.text,
)
async def fanart_add_stock(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    try:
        stock = int(
            message.text.strip()
        )
    except ValueError:
        await message.answer(
            "❌ موجودی باید عدد صحیح باشد."
        )
        return

    if stock <= 0:
        await message.answer(
            "❌ موجودی باید بیشتر از صفر باشد."
        )
        return

    await state.update_data(
        stock=stock,
    )

    await create_fan_art(
        message,
        state,
    )


async def create_fan_art(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    required = [
        "image_file_id",
        "name",
        "description",
        "rarity",
        "price",
        "value_gold",
        "is_limited",
    ]

    if any(
        key not in data
        for key in required
    ):
        await state.clear()

        await message.answer(
            "❌ اطلاعات Fan Art ناقص است.\n"
            "دوباره /fanart_add را اجرا کن."
        )

        return

    async with AsyncSessionLocal() as session:
        fan_art = FanArt(
            name=data["name"],
            description=data["description"],
            image_file_id=data["image_file_id"],
            rarity=data["rarity"],
            price=data["price"],
            value_gold=int(data["value_gold"]),
            is_active=True,
            is_limited=data["is_limited"],
            stock=data.get("stock"),
            display_order=0,
        )

        session.add(fan_art)

        await session.commit()
        await session.refresh(fan_art)

        fan_art_id = fan_art.id

    await state.clear()

    if data["is_limited"]:
        stock_text = str(
            data.get("stock")
        )
    else:
        stock_text = "نامحدود"

    await message.answer(
        "✅ Fan Art با موفقیت اضافه شد.\n\n"
        f"🆔 ID: {fan_art_id}\n"
        f"🎨 نام: {data['name']}\n"
        f"💎 رریتی: {data['rarity']}\n"
        f"💰 قیمت: {data['price']}\n"
        f"🗃 موجودی: {stock_text}"
    )


@router.callback_query(
    F.data.startswith("fanartadmin:approve:")
)
async def fanart_admin_approve(
    callback: CallbackQuery,
):
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    try:
        order_id = int(
            callback.data.split(":")[-1]
        )
    except ValueError:
        await callback.answer(
            "شناسه سفارش نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        order = await approve_order(
            order_id,
        )
    except ValueError as exc:
        if str(exc) == "OUT_OF_STOCK":
            await callback.answer(
                "موجودی این Fan Art تمام شده است.",
                show_alert=True,
            )
            return

        await callback.answer(
            "خطا در تأیید سفارش.",
            show_alert=True,
        )
        return

    if order is None:
        await callback.answer(
            "این سفارش دیگر قابل تأیید نیست.",
            show_alert=True,
        )
        return

    caption = (
        "✅ سفارش تأیید شد.\n\n"
        f"🆔 سفارش: {order.order_code}\n"
        f"🎨 Fan Art: {order.fan_art.name}\n"
        f"💰 مبلغ: {order.price_snapshot}\n"
        f"👤 Telegram ID: {order.telegram_id}\n"
        f"📌 وضعیت: {APPROVED}"
    )

    try:
        await callback.message.edit_caption(
            caption=caption,
            reply_markup=None,
        )
    except Exception:
        try:
            await callback.message.edit_text(
                caption,
            )
        except Exception:
            pass

    try:
        await callback.bot.send_message(
            chat_id=order.telegram_id,
            text=(
                "🎉 خرید Fan Art شما تأیید شد!\n\n"
                f"🎨 {order.fan_art.name}\n"
                f"🆔 سفارش: {order.order_code}\n\n"
                "Fan Art به صندوقچه شما اضافه شد."
            ),
        )
    except Exception:
        pass

    await callback.answer(
        "✅ سفارش تأیید شد."
    )


@router.callback_query(
    F.data.startswith("fanartadmin:reject:")
)
async def fanart_admin_reject_start(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "دسترسی ندارید.",
            show_alert=True,
        )
        return

    try:
        order_id = int(
            callback.data.split(":")[-1]
        )
    except ValueError:
        await callback.answer(
            "شناسه سفارش نامعتبر است.",
            show_alert=True,
        )
        return

    await state.clear()

    await state.update_data(
        reject_order_id=order_id,
    )

    await state.set_state(
        FanArtAdminStates.reject_reason,
    )

    await callback.message.answer(
        f"❌ دلیل رد سفارش #{order_id} را ارسال کن."
    )

    await callback.answer()


@router.message(
    FanArtAdminStates.reject_reason,
    F.text,
)
async def fanart_admin_reject_finish(
    message: Message,
    state: FSMContext,
):
    if not is_admin(
        message.from_user.id
    ):
        return

    data = await state.get_data()

    order_id = data.get(
        "reject_order_id"
    )

    if not order_id:
        await state.clear()

        await message.answer(
            "❌ سفارش پیدا نشد."
        )

        return

    reason = message.text.strip()

    if not reason:
        await message.answer(
            "❌ دلیل رد نمی‌تواند خالی باشد."
        )
        return

    order = await reject_order(
        order_id=order_id,
        reason=reason,
    )

    await state.clear()

    if order is None:
        await message.answer(
            "❌ این سفارش دیگر قابل رد کردن نیست."
        )
        return

    await message.answer(
        "❌ سفارش رد شد.\n\n"
        f"🆔 سفارش: {order.order_code}\n"
        f"🎨 Fan Art: {order.fan_art.name}\n"
        f"📌 دلیل: {reason}"
    )

    try:
        await message.bot.send_message(
            chat_id=order.telegram_id,
            text=(
                "❌ سفارش Fan Art شما رد شد.\n\n"
                f"🎨 {order.fan_art.name}\n"
                f"🆔 سفارش: {order.order_code}\n"
                f"📌 دلیل: {reason}"
            ),
        )
    except Exception:
        pass