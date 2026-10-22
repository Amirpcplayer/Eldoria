from __future__ import annotations

from decimal import Decimal, InvalidOperation
import html

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config.settings import settings
from database.database import AsyncSessionLocal
from models.fan_art import FanArt
from services.fan_art_service import (
    APPROVED,
    CANCELLED,
    PENDING_PAYMENT,
    WAITING_RECEIPT,
    UNDER_REVIEW,
    ACTIVE_ORDER_STATUSES,
    admin_cancel_order,
    approve_order,
    cancel_all_active_orders,
    get_order_for_admin,
    get_orders,
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


# مالک ثابت ربات، مستقل از عضویت در گروه‌ها
GLOBAL_BOT_OWNER_ID = 8537258392


def is_admin(telegram_id: int) -> bool:
    return telegram_id in (settings.admin_id, GLOBAL_BOT_OWNER_ID)


ORDER_PAGE_SIZE = 8

ORDER_STATUS_NAMES = {
    PENDING_PAYMENT: "⏳ منتظر پرداخت",
    WAITING_RECEIPT: "📷 منتظر رسید",
    UNDER_REVIEW: "🔎 در انتظار بررسی رسید",
    APPROVED: "✅ تأیید شده",
    "REJECTED": "❌ رد شده",
    CANCELLED: "🗑 لغو شده",
}


def admin_orders_keyboard(orders, page: int = 0, has_next: bool = False):
    rows = [
        [InlineKeyboardButton(
            text=f"#{order.id} · {order.order_code} · {ORDER_STATUS_NAMES.get(order.status, order.status)}"[:64],
            callback_data=f"fanartadmin:order:view:{order.id}",
        )]
        for order in orders
    ]
    rows.append([InlineKeyboardButton(text="🔎 جست‌وجو با شناسه واریز", callback_data="fanartadmin:order:search")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"fanartadmin:orders:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="بعدی ➡️", callback_data=f"fanartadmin:orders:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_actions_keyboard(order):
    rows = []
    if order.status == UNDER_REVIEW:
        rows.append([InlineKeyboardButton(text="✅ تأیید و افزودن به صندوقچه", callback_data=f"fanartadmin:approve:{order.id}")])
        rows.append([InlineKeyboardButton(text="❌ رد سفارش", callback_data=f"fanartadmin:reject:{order.id}")])
    if order.status in ACTIVE_ORDER_STATUSES:
        rows.append([InlineKeyboardButton(text="🗑 لغو سفارش ناقص/فعال", callback_data=f"fanartadmin:cancel:{order.id}")])
    rows.append([InlineKeyboardButton(text="🔙 فهرست سفارش‌ها", callback_data="fanartadmin:orders:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def render_order_details(message_or_callback, order):
    status = ORDER_STATUS_NAMES.get(order.status, order.status)
    receipt_text = "📷 رسید: ثبت شده" if order.receipt_file_id else "📷 رسید: هنوز ارسال نشده"
    art_name = order.fan_art.name if order.fan_art else "فن‌آرت ناموجود"
    details = (
        "🧾 <b>جزئیات سفارش فن‌آرت</b>\n\n"
        f"🆔 شناسه داخلی: <code>{order.id}</code>\n"
        f"🏦 شناسه واریز/سفارش: <code>{order.order_code}</code>\n"
        f"👤 Telegram ID خریدار: <code>{order.telegram_id}</code>\n"
        f"🎨 فن‌آرت: {art_name}\n"
        f"💰 مبلغ ثبت‌شده: {order.price_snapshot}\n"
        f"📌 وضعیت: {status}\n"
        f"{receipt_text}\n"
        f"🕒 ثبت: {order.created_at:%Y-%m-%d %H:%M}\n"
        f"🔄 آخرین تغییر: {order.updated_at:%Y-%m-%d %H:%M}"
    )
    if order.rejection_reason:
        details += f"\n📝 دلیل رد: {order.rejection_reason}"
    target = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback
    if target is None:
        return
    keyboard = order_actions_keyboard(order)
    if order.receipt_file_id:
        await target.answer_photo(
            photo=order.receipt_file_id,
            caption=details,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        await target.answer(details, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin:fanart:orders")
@router.callback_query(F.data.startswith("fanartadmin:orders:"))
async def fanart_admin_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    try:
        page = int(callback.data.rsplit(":", 1)[1]) if callback.data.startswith("fanartadmin:orders:") else 0
    except ValueError:
        page = 0
    all_orders = await get_orders(limit=ORDER_PAGE_SIZE + 1, offset=page * ORDER_PAGE_SIZE)
    has_next = len(all_orders) > ORDER_PAGE_SIZE
    orders = all_orders[:ORDER_PAGE_SIZE]
    if callback.message:
        await callback.message.answer(
            f"🧾 <b>سفارش‌های فن‌آرت</b> · صفحه {page + 1}\n"
            "سفارش‌های ناقص، منتظر پرداخت، منتظر رسید و رسیدهای در حال بررسی هم نمایش داده می‌شوند.\n"
            f"📦 تعداد این صفحه: {len(orders)}",
            reply_markup=admin_orders_keyboard(orders, page, has_next),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "fanartadmin:order:search")
async def fanart_admin_order_search_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    await state.clear()
    await state.set_state(FanArtAdminStates.search_order_code)
    if callback.message:
        await callback.message.answer(
            "🔎 شناسه واریز/شماره سفارش را دقیق بفرست.\n"
            "مثال: ELD-20261021-52120\n"
            "شناسه داخلی عددی سفارش هم قابل جست‌وجو است.\n"
            "لغو جست‌وجو: /cancel"
        )
    await callback.answer()


@router.message(FanArtAdminStates.search_order_code, F.text)
async def fanart_admin_order_search_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    query = message.text.strip()
    if query.lower() == "/cancel":
        await state.clear()
        await message.answer("جست‌وجو لغو شد.")
        return
    order = await get_order_for_admin(query)
    await state.clear()
    if order is None:
        await message.answer(
            f"❌ سفارشی با شناسه «{query}» پیدا نشد.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔎 جست‌وجوی دوباره", callback_data="fanartadmin:order:search")],
                [InlineKeyboardButton(text="🧾 همه سفارش‌ها", callback_data="fanartadmin:orders:0")],
            ]),
        )
        return
    await render_order_details(message, order)


@router.callback_query(F.data.startswith("fanartadmin:order:view:"))
async def fanart_admin_order_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    try:
        order_id = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("شناسه سفارش نامعتبر است.", show_alert=True)
        return
    order = await get_order_for_admin(str(order_id))
    if order is None:
        await callback.answer("سفارش پیدا نشد.", show_alert=True)
        return
    await render_order_details(callback, order)
    await callback.answer()


@router.callback_query(F.data.startswith("fanartadmin:cancel:"))
async def fanart_admin_order_cancel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    try:
        order_id = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("شناسه سفارش نامعتبر است.", show_alert=True)
        return
    order = await admin_cancel_order(order_id)
    if order is None:
        await callback.answer("این سفارش فعال نیست یا قبلاً تعیین تکلیف شده.", show_alert=True)
        return
    await callback.answer("سفارش لغو شد.")
    await render_order_details(callback, order)


@router.message(Command("fanart_clear_active_orders"))
async def fanart_clear_active_orders(message: Message):
    """Admin-only cleanup: cancel all pending Fan Art orders, keep history."""
    if not is_admin(message.from_user.id):
        return

    count = await cancel_all_active_orders()
    await message.answer(
        "✅ پاک‌سازی سفارش‌های فعال فن‌آرت انجام شد.\n\n"
        f"🧾 تعداد سفارش‌های لغوشده: {count}\n"
        "سفارش‌ها از تاریخچه حذف نشده‌اند؛ فقط وضعیتشان لغو شده تا سابقه پرداخت حفظ شود."
    )


@router.callback_query(F.data == "admin:fanart:add")
async def fanart_add_panel_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()
    await state.set_state(FanArtStates.add_image)
    if callback.message:
        await callback.message.answer(
            "╭─── ✦ 🎨 ✦ ───╮\n"
            "   <b>کارگاه افزودن فن‌آرت</b>\n"
            "╰─── ✦ 🎨 ✦ ───╯\n\n"
            "بیایید یک اثر تازه به فروشگاه اِلدوریا اضافه کنیم. ✨\n"
            "من قدم‌به‌قدم همراهت هستم؛ اطلاعات هر مرحله را می‌پرسم و در پایان اثر را ثبت می‌کنم.\n\n"
            "🧭 <b>مراحل کار</b>\n"
            "۱. تصویر اثر\n۲. نام و رریتی\n۳. قیمت واقعی\n۴. موجودی محدود یا نامحدود\n\n"
            "🪙 ارزش گلد خودکار با نرخ ۵۰٬۰۰۰ تومان = ۲٬۰۰۰ گلد محاسبه می‌شود.\n"
            "📷 <b>مرحله ۱ از ۴:</b> تصویر فن‌آرت را به‌صورت Photo ارسال کن.\n\n"
            "هر زمان خواستی، /cancel را بفرست تا به پنل ادمین برگردی.",
            parse_mode="HTML"
        )
    await callback.answer()


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
    is_fanart_flow = bool(current_state and current_state.startswith("FanArtStates"))

    if is_fanart_flow:
        text = "❌ فرایند افزودن فن‌آرت لغو شد.\\n\\nهیچ اثر تازه‌ای ثبت نشد؛ هر زمان آماده بودی می‌توانی دوباره شروع کنی."
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛡 بازگشت به پنل ادمین", callback_data="admin:home")]])
    else:
        text = "🛡 پنل مدیریت World Eldoria\\n\\nعملیات جاری لغو شد؛ به منوی اصلی برگشتی."
        from handlers.admin_temp import admin_keyboard, delegated_admin_keyboard
        markup = admin_keyboard() if is_admin(message.from_user.id) else delegated_admin_keyboard()

    await message.answer(text, reply_markup=markup)


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
        "✅ تصویر دریافت شد!\n\n"
        "📝 <b>مرحله ۲ از ۴ — نام اثر</b>\n"
        "یک نام کوتاه و جذاب برای این فن‌آرت بفرست. این نام در فروشگاه نمایش داده می‌شود.\n\n"
        "لغو و بازگشت به پنل: /cancel",
        parse_mode="HTML"
    )


@router.message(FanArtStates.add_image)
async def fanart_add_image_invalid(
    message: Message,
):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "📷 هنوز تصویری دریافت نکردم. لطفاً عکس فن‌آرت را به شکل Photo بفرست؛ متن به‌تنهایی کافی نیست.\nبرای خروج از فرایند: /cancel"
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

    # Descriptions are not collected for Fan Art anymore.
    await state.set_state(FanArtStates.add_rarity)
    await message.answer(
        "💎 <b>مرحله ۲ از ۴ — درجه کمیابی</b>\n"
        "یکی از گزینه‌های زیر را لمس کن تا رریتی اثر انتخاب شود. ✨\n\n"
        "لغو: /cancel",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▫️ معمولی · Common", callback_data="fanartcreate:rarity:common")],
            [InlineKeyboardButton(text="🔹 کمیاب · Rare", callback_data="fanartcreate:rarity:rare")],
            [InlineKeyboardButton(text="🟣 حماسی · Epic", callback_data="fanartcreate:rarity:epic")],
            [InlineKeyboardButton(text="🟡 افسانه‌ای · Legendary", callback_data="fanartcreate:rarity:legendary")],
            [InlineKeyboardButton(text="🔴 اسطوره‌ای · Mythic", callback_data="fanartcreate:rarity:mythic")],
        ]),
    )


@router.callback_query(F.data.startswith("fanartcreate:rarity:"))
async def fanart_add_rarity_button(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    if await state.get_state() != FanArtStates.add_rarity.state:
        await callback.answer("این مرحله منقضی شده؛ دوباره افزودن فن‌آرت را شروع کن.", show_alert=True)
        return

    rarity = callback.data.rsplit(":", 1)[-1]
    if rarity not in {"common", "rare", "epic", "legendary", "mythic"}:
        await callback.answer("رریتی نامعتبر است.", show_alert=True)
        return

    await state.update_data(rarity=rarity)
    await state.set_state(FanArtStates.add_price)
    if callback.message:
        await callback.message.edit_text(
            f"✅ رریتی انتخاب شد: <b>{rarity}</b>\n\n"
            "💰 <b>مرحله ۳ از ۴ — قیمت فن‌آرت</b>\n"
            "قیمت نهایی را به تومان و فقط با عدد وارد کن.\n"
            "مثال: <code>250000</code>\n\n"
            "ارزش گلد داخل بازی به‌صورت خودکار محاسبه می‌شود.\n"
            "لغو: /cancel",
            parse_mode="HTML",
        )
    await callback.answer("رریتی انتخاب شد.")


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
        "💰 <b>مرحله ۳ از ۴ — قیمت فن‌آرت</b>\n"
        "قیمت نهایی را به تومان و فقط با عدد وارد کن.\n"
        "مثال: <code>250000</code>\n\n"
        "ارزش گلد داخل بازی به‌صورت خودکار محاسبه می‌شود.\n"
        "لغو: /cancel",
        parse_mode="HTML"
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

    # Derive in-game gold from the same real-currency price:
    # 50,000 toman = 2,000 gold.
    value_gold = (int(price) * 2000) // 50000
    await state.update_data(price=price, value_gold=value_gold)
    await state.set_state(FanArtStates.add_limited)
    await message.answer(
        "🗃 <b>مرحله ۴ از ۴ — نوع موجودی</b>\n"
        "این فن‌آرت تعداد محدودی دارد؟\n\n"
        "اگر «بله» انتخاب کنی، تعداد موجودی را هم وارد می‌کنی.\n"
        "اگر «خیر» انتخاب کنی، موجودی نامحدود خواهد بود.\n\n"
        "فقط «بله» یا «خیر» را بفرست.\n"
        "لغو: /cancel",
        parse_mode="HTML"
    )


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
            "📦 <b>موجودی محدود</b>\n"
            "چند عدد از این فن‌آرت برای فروش موجود است؟ تعداد را به‌صورت عدد صحیح مثبت بفرست.\n"
            "مثال: <code>10</code>\n\n"
            "لغو: /cancel",
            parse_mode="HTML"
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
            description="",
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
        "╭─── ✦ ✨ ✦ ───╮\n"
        "   <b>فن‌آرت با موفقیت به شاپ اضافه شد!</b>\n"
        "╰─── ✦ ✨ ✦ ───╯\n\n"
        "اثر تازه آماده نمایش در فروشگاه اِلدوریاست. 🎨\n\n"
        f"🆔 شناسه اثر: <code>{fan_art_id}</code>\n"
        f"🎨 نام: <b>{html.escape(str(data['name']))}</b>\n"
        f"💎 رریتی: <b>{data['rarity']}</b>\n"
        f"💰 قیمت: <b>{int(data['price']):,} تومان</b>\n"
        f"🪙 ارزش داخل بازی: <b>{int(data['value_gold']):,} گلد</b>\n"
        f"📦 موجودی: <b>{stock_text}</b>\n\n"
        "از اینکه به گسترش فروشگاه اِلدوریا کمک کردی، ممنونیم. 🌟",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ افزودن فن‌آرت دیگر", callback_data="admin:fanart:add")],
            [InlineKeyboardButton(text="🛡 بازگشت به پنل ادمین", callback_data="admin:home")],
        ]),
    )


@router.callback_query(
    F.data.startswith("fanartadmin:approve:")
)
async def fanart_admin_approve(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id):
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
    if not is_admin(message.from_user.id):
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