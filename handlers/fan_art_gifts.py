from __future__ import annotations

import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select, distinct

from config.settings import settings
from database.database import AsyncSessionLocal
from models.character import Character
from models.fan_art import FanArt, FanArtOwnership
from states.fan_art_gift import FanArtGiftStates


router = Router()
logger = logging.getLogger(__name__)


# ترتیب نمایش سطح‌ها در تمام بخش‌های گیفت
RARITIES = {
    "common": "⚪ Common",
    "rare": "🔵 Rare",
    "epic": "🟣 Epic",
    "legendary": "🟠 Legendary",
    "mythic": "🔴 Mythic",
}

RARITY_ORDER = {
    "common": 0,
    "rare": 1,
    "epic": 2,
    "legendary": 3,
    "mythic": 4,
}


def is_admin(telegram_id: int) -> bool:
    return telegram_id == settings.admin_id


def rarity_name(rarity: str) -> str:
    return RARITIES.get(rarity, rarity)


def sort_rarities(rarities: list[str]) -> list[str]:
    """مرتب‌سازی سطح‌ها بر اساس ترتیب بازی، نه حروف الفبا."""
    return sorted(
        rarities,
        key=lambda rarity: RARITY_ORDER.get(rarity, 999),
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ لغو عملیات",
                    callback_data="admin:gift:cancel",
                )
            ]
        ]
    )


def rarity_keyboard(prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"{prefix}:{rarity}",
            )
        ]
        for rarity, label in RARITIES.items()
    ]

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ لغو",
                callback_data="admin:gift:cancel",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirmation_keyboard(mode: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید و ارسال گیفت",
                    callback_data=f"admin:gift:confirm:{mode}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو عملیات",
                    callback_data="admin:gift:cancel",
                )
            ],
        ]
    )


def player_search_keyboard(mode: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔎 جست‌وجوی دوباره",
                    callback_data=f"admin:gift:search:{mode}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 نمایش فهرست پلیرها",
                    callback_data=f"admin:gift:players:{mode}:0",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو عملیات",
                    callback_data="admin:gift:cancel",
                )
            ],
        ]
    )


async def player_keyboard(
    mode: str,
    page: int = 0,
) -> InlineKeyboardMarkup:
    page_size = 8
    page = max(0, page)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Character)
            .order_by(Character.id.desc())
            .offset(page * page_size)
            .limit(page_size + 1)
        )
        characters = list(result.scalars().all())

    has_next = len(characters) > page_size
    characters = characters[:page_size]

    rows = [
        [
            InlineKeyboardButton(
                text="🔎 جست‌وجوی پلیر با یوزرنیم یا شناسه",
                callback_data=f"admin:gift:search:{mode}",
            )
        ]
    ]

    for character in characters:
        username = getattr(character, "telegram_username", None)
        username_text = f" · @{username}" if username else ""

        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"👤 {character.name} "
                        f"· Lv.{character.level}"
                        f"{username_text}"
                    )[:64],
                    callback_data=(
                        f"admin:gift:player:"
                        f"{mode}:{character.telegram_id}"
                    ),
                )
            ]
        )

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ قبلی",
                callback_data=f"admin:gift:players:{mode}:{page - 1}",
            )
        )

    if has_next:
        navigation.append(
            InlineKeyboardButton(
                text="بعدی ➡️",
                callback_data=f"admin:gift:players:{mode}:{page + 1}",
            )
        )

    if navigation:
        rows.append(navigation)

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ لغو عملیات",
                callback_data="admin:gift:cancel",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_players(
    callback: CallbackQuery,
    mode: str,
    page: int = 0,
) -> None:
    if mode not in {"direct", "shop"}:
        await callback.answer(
            "نوع گیفت نامعتبر است.",
            show_alert=True,
        )
        return

    keyboard = await player_keyboard(mode, page)

    async with AsyncSessionLocal() as session:
        player_count = await session.scalar(
            select(Character.telegram_id).limit(1)
        )

    if player_count is None:
        if callback.message:
            await callback.message.edit_text(
                "هنوز هیچ پلیر ثبت نشده است.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="❌ لغو عملیات",
                                callback_data="admin:gift:cancel",
                            )
                        ]
                    ]
                ),
            )

        await callback.answer()
        return

    text = (
        "👤 پلیر دریافت‌کننده گیفت را انتخاب کن.\n\n"
        "می‌توانی از فهرست استفاده کنی یا با یوزرنیم و شناسه تلگرام "
        "پلیر را جست‌وجو کنی."
    )

    if callback.message:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
        )

    await callback.answer()


# ============================================================
# منوی اصلی گیفت فن‌آرت
# ============================================================

@router.callback_query(F.data == "admin:fanart_gifts")
async def open_gift_menu(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎨 ساخت فن‌آرت و گیفت مستقیم",
                    callback_data="admin:gift:direct",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎁 گیفت از فن‌آرت‌های شاپ",
                    callback_data="admin:gift:shop",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ بازگشت به پنل ادمین",
                    callback_data="admin:home",
                )
            ],
        ]
    )

    if callback.message:
        await callback.message.edit_text(
            "🎁 مدیریت گیفت فن‌آرت\n\n"
            "روش موردنظرت را انتخاب کن:",
            reply_markup=keyboard,
        )

    await callback.answer()


# ============================================================
# جست‌وجوی پلیر برای هر دو روش گیفت
# ============================================================

@router.callback_query(F.data.startswith("admin:gift:search:"))
async def start_gift_player_search(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    mode = callback.data.rsplit(":", 1)[-1]

    if mode not in {"direct", "shop"}:
        await callback.answer("نوع گیفت نامعتبر است.", show_alert=True)
        return

    current_state = await state.get_state()

    expected_state = (
        FanArtGiftStates.create_player.state
        if mode == "direct"
        else FanArtGiftStates.shop_player.state
    )

    if current_state != expected_state:
        await callback.answer(
            "مرحله انتخاب پلیر منقضی شده است؛ عملیات را دوباره شروع کن.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_text(
            "🔎 جست‌وجوی پلیر\n\n"
            "یوزرنیم پلیر را با یا بدون @ بفرست، "
            "یا شناسه عددی تلگرام او را وارد کن.\n\n"
            "مثال:\n"
            "@player_username\n"
            "123456789",
            reply_markup=player_search_keyboard(mode),
        )

    await callback.answer()


@router.message(FanArtGiftStates.create_player, F.text)
@router.message(FanArtGiftStates.shop_player, F.text)
async def search_gift_player_submit(
    message: Message,
    state: FSMContext,
):
    if not message.from_user or not is_admin(message.from_user.id):
        return

    current_state = await state.get_state()

    if current_state == FanArtGiftStates.create_player.state:
        mode = "direct"
    elif current_state == FanArtGiftStates.shop_player.state:
        mode = "shop"
    else:
        return

    raw_query = (message.text or "").strip()

    if not raw_query:
        await message.answer(
            "❌ لطفاً یوزرنیم یا شناسه عددی تلگرام را وارد کن."
        )
        return

    # پذیرش username با یا بدون @
    username_query = raw_query.lstrip("@").strip().lower()

    async with AsyncSessionLocal() as session:
        character = None

        # اگر ورودی عددی باشد، ابتدا شناسه دقیق تلگرام بررسی می‌شود.
        if raw_query.isdigit():
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == int(raw_query)
                )
            )

        # در صورت پیدا نشدن شناسه، یوزرنیم دقیق بررسی می‌شود.
        if character is None and username_query:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_username == username_query
                )
            )

        # برای ورودی عددی، در صورت نبودن نتیجه با شناسه،
        # جست‌وجوی یوزرنیم هم انجام شده است.

        if character is not None:
            found_characters = [character]
        else:
            found_characters = []

    if not found_characters:
        await message.answer(
            "❌ پلیر با این یوزرنیم یا شناسه پیدا نشد.\n\n"
            "ورودی را بررسی کن یا دوباره جست‌وجو کن.",
            reply_markup=player_search_keyboard(mode),
        )
        return

    rows = []

    for character in found_characters:
        username = getattr(character, "telegram_username", None)
        username_text = f" · @{username}" if username else ""

        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"👤 {character.name} · Lv.{character.level}"
                        f"{username_text}"
                    )[:64],
                    callback_data=(
                        f"admin:gift:player:"
                        f"{mode}:{character.telegram_id}"
                    ),
                )
            ]
        )

    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="🔎 جست‌وجوی دوباره",
                    callback_data=f"admin:gift:search:{mode}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 نمایش فهرست پلیرها",
                    callback_data=f"admin:gift:players:{mode}:0",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو عملیات",
                    callback_data="admin:gift:cancel",
                )
            ],
        ]
    )

    await message.answer(
        "✅ پلیر پیدا شد. برای ادامه گیفت، او را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


# ============================================================
# روش اول: ساخت فن‌آرت و گیفت مستقیم
# ============================================================

@router.callback_query(F.data == "admin:gift:direct")
async def start_direct_gift(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()
    await state.set_state(FanArtGiftStates.create_image)

    if callback.message:
        await callback.message.answer(
            "🎨 ساخت فن‌آرت برای گیفت\n\n"
            "مرحله ۱ از ۵: عکس فن‌آرت را به‌صورت Photo ارسال کن.",
            reply_markup=cancel_keyboard(),
        )

    await callback.answer()


@router.message(FanArtGiftStates.create_image, F.photo)
async def direct_gift_image(
    message: Message,
    state: FSMContext,
):
    if not message.from_user or not is_admin(message.from_user.id):
        return

    await state.update_data(image_file_id=message.photo[-1].file_id)
    await state.set_state(FanArtGiftStates.create_name)

    await message.answer("مرحله ۲ از ۵: نام فن‌آرت را ارسال کن.")


@router.message(FanArtGiftStates.create_image)
async def direct_gift_image_invalid(message: Message):
    if message.from_user and is_admin(message.from_user.id):
        await message.answer("❌ لطفاً عکس فن‌آرت را به‌صورت Photo ارسال کن.")


@router.message(FanArtGiftStates.create_name, F.text)
async def direct_gift_name(
    message: Message,
    state: FSMContext,
):
    if not message.from_user or not is_admin(message.from_user.id):
        return

    name = message.text.strip()

    if not name or len(name) > 150:
        await message.answer("❌ نام باید بین ۱ تا ۱۵۰ نویسه باشد.")
        return

    await state.update_data(name=name)
    await state.set_state(FanArtGiftStates.create_description)

    await message.answer("مرحله ۳ از ۵: توضیحات فن‌آرت را ارسال کن.")


@router.message(FanArtGiftStates.create_description, F.text)
async def direct_gift_description(
    message: Message,
    state: FSMContext,
):
    if not message.from_user or not is_admin(message.from_user.id):
        return

    description = message.text.strip()

    if not description:
        await message.answer("❌ توضیحات نمی‌تواند خالی باشد.")
        return

    await state.update_data(description=description)
    await state.set_state(FanArtGiftStates.create_rarity)

    await message.answer(
        "مرحله ۴ از ۵: سطح فن‌آرت را انتخاب کن.",
        reply_markup=rarity_keyboard("admin:gift:direct_rarity"),
    )


@router.callback_query(F.data.startswith("admin:gift:direct_rarity:"))
async def direct_gift_rarity(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    rarity = callback.data.rsplit(":", 1)[-1]

    if rarity not in RARITIES:
        await callback.answer("سطح انتخاب‌شده معتبر نیست.", show_alert=True)
        return

    current_state = await state.get_state()

    if current_state != FanArtGiftStates.create_rarity.state:
        await callback.answer(
            "این مرحله منقضی شده است. دوباره شروع کن.",
            show_alert=True,
        )
        return

    await state.update_data(rarity=rarity, gift_mode="direct")
    await state.set_state(FanArtGiftStates.create_player)

    await show_players(callback, "direct")


# ============================================================
# روش دوم: گیفت از فن‌آرت‌های موجود در شاپ
# ============================================================

@router.callback_query(F.data == "admin:gift:shop")
async def start_shop_gift(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()
    await state.set_state(FanArtGiftStates.shop_player)

    await show_players(callback, "shop")


@router.callback_query(F.data.startswith("admin:gift:players:"))
async def gift_players_page(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    parts = callback.data.split(":")

    try:
        mode = parts[3]
        page = int(parts[4])
    except (ValueError, IndexError):
        await callback.answer("اطلاعات صفحه نامعتبر است.", show_alert=True)
        return

    if mode not in {"direct", "shop"}:
        await callback.answer("نوع گیفت نامعتبر است.", show_alert=True)
        return

    current_state = await state.get_state()
    expected_state = (
        FanArtGiftStates.create_player.state
        if mode == "direct"
        else FanArtGiftStates.shop_player.state
    )

    if current_state != expected_state:
        await callback.answer(
            "مرحله انتخاب پلیر منقضی شده است.",
            show_alert=True,
        )
        return

    await show_players(callback, mode, page)


@router.callback_query(F.data.startswith("admin:gift:player:"))
async def choose_gift_player(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    parts = callback.data.split(":")

    try:
        mode = parts[3]
        telegram_id = int(parts[4])
    except (ValueError, IndexError):
        await callback.answer("اطلاعات پلیر نامعتبر است.", show_alert=True)
        return

    if mode not in {"direct", "shop"}:
        await callback.answer("نوع گیفت نامعتبر است.", show_alert=True)
        return

    current_state = await state.get_state()

    if mode == "direct":
        if current_state != FanArtGiftStates.create_player.state:
            await callback.answer(
                "مرحله انتخاب پلیر منقضی شده است.",
                show_alert=True,
            )
            return
    else:
        if current_state != FanArtGiftStates.shop_player.state:
            await callback.answer(
                "مرحله انتخاب پلیر منقضی شده است.",
                show_alert=True,
            )
            return

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == telegram_id)
        )

    if character is None:
        await callback.answer("این پلیر پیدا نشد.", show_alert=True)
        return

    await state.update_data(
        recipient_telegram_id=telegram_id,
        recipient_name=character.name,
        gift_mode=mode,
    )

    if mode == "direct":
        data = await state.get_data()

        required = ("image_file_id", "name", "description", "rarity")

        if any(key not in data for key in required):
            await callback.answer(
                "اطلاعات فن‌آرت ناقص است؛ عملیات را دوباره شروع کن.",
                show_alert=True,
            )
            await state.clear()
            return

        await state.set_state(FanArtGiftStates.confirm_gift)

        if callback.message:
            await callback.message.edit_text(
                "📋 تأیید ساخت فن‌آرت و گیفت\n\n"
                f"🎨 نام: {data['name']}\n"
                f"💎 سطح: {rarity_name(data['rarity'])}\n"
                f"👤 دریافت‌کننده: {character.name}\n\n"
                "این فن‌آرت به‌صورت اختصاصی برای گیفت ساخته می‌شود "
                "و در شاپ برای فروش قرار نمی‌گیرد.\n"
                "💰 هزینه پلیر: ۰",
                reply_markup=confirmation_keyboard("direct"),
            )

        await callback.answer()
        return

    await state.set_state(FanArtGiftStates.shop_rarity)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(distinct(FanArt.rarity)).where(
                FanArt.is_active.is_(True)
            )
        )
        rarities = sort_rarities(
            [
                rarity
                for rarity in result.scalars().all()
                if rarity in RARITIES
            ]
        )

    if not rarities:
        await state.clear()
        await callback.answer(
            "هیچ فن‌آرت فعالی در شاپ وجود ندارد.",
            show_alert=True,
        )
        return

    rows = [
        [
            InlineKeyboardButton(
                text=rarity_name(rarity),
                callback_data=f"admin:gift:shop_rarity:{rarity}",
            )
        ]
        for rarity in rarities
    ]

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ لغو عملیات",
                callback_data="admin:gift:cancel",
            )
        ]
    )

    if callback.message:
        await callback.message.edit_text(
            f"👤 دریافت‌کننده: {character.name}\n\n"
            "💎 سطح فن‌آرت‌های شاپ را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin:gift:shop_rarity:"))
async def choose_shop_rarity(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    current_state = await state.get_state()

    if current_state != FanArtGiftStates.shop_rarity.state:
        await callback.answer(
            "مرحله انتخاب سطح منقضی شده است.",
            show_alert=True,
        )
        return

    rarity = callback.data.rsplit(":", 1)[-1]

    if rarity not in RARITIES:
        await callback.answer("سطح انتخاب‌شده معتبر نیست.", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FanArt)
            .where(
                FanArt.is_active.is_(True),
                FanArt.rarity == rarity,
            )
            .order_by(
                FanArt.display_order.asc(),
                FanArt.id.asc(),
            )
        )
        fan_arts = list(result.scalars().all())

    if not fan_arts:
        await callback.answer(
            "در این سطح فن‌آرت فعالی وجود ندارد.",
            show_alert=True,
        )
        return

    await state.update_data(shop_rarity=rarity)
    await state.set_state(FanArtGiftStates.shop_art)

    rows = [
        [
            InlineKeyboardButton(
                text=f"🎨 {art.name} · #{art.id}"[:64],
                callback_data=f"admin:gift:shop_art:{art.id}",
            )
        ]
        for art in fan_arts
    ]

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ لغو عملیات",
                callback_data="admin:gift:cancel",
            )
        ]
    )

    if callback.message:
        await callback.message.edit_text(
            f"💎 سطح: {rarity_name(rarity)}\n\n"
            "فن‌آرت موردنظر را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin:gift:shop_art:"))
async def choose_shop_art(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    current_state = await state.get_state()

    if current_state != FanArtGiftStates.shop_art.state:
        await callback.answer(
            "مرحله انتخاب فن‌آرت منقضی شده است.",
            show_alert=True,
        )
        return

    try:
        fan_art_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer("شناسه فن‌آرت نامعتبر است.", show_alert=True)
        return

    data = await state.get_data()
    expected_rarity = data.get("shop_rarity")

    async with AsyncSessionLocal() as session:
        fan_art = await session.scalar(
            select(FanArt).where(
                FanArt.id == fan_art_id,
                FanArt.is_active.is_(True),
            )
        )

    if fan_art is None:
        await callback.answer(
            "این فن‌آرت دیگر در شاپ فعال نیست.",
            show_alert=True,
        )
        return

    if fan_art.rarity != expected_rarity:
        await callback.answer(
            "این فن‌آرت متعلق به سطح انتخاب‌شده نیست.",
            show_alert=True,
        )
        return

    await state.update_data(
        shop_fan_art_id=fan_art.id,
        shop_fan_art_name=fan_art.name,
        shop_fan_art_image=fan_art.image_file_id,
        shop_fan_art_description=fan_art.description,
        shop_fan_art_rarity=fan_art.rarity,
        gift_mode="shop",
    )

    await state.set_state(FanArtGiftStates.confirm_gift)

    if callback.message:
        await callback.message.edit_text(
            "📋 تأیید گیفت از شاپ\n\n"
            f"👤 دریافت‌کننده: {data.get('recipient_name', 'نامشخص')}\n"
            f"🎨 فن‌آرت: {fan_art.name}\n"
            f"💎 سطح: {rarity_name(fan_art.rarity)}\n\n"
            "💰 هزینه پلیر: ۰\n"
            "📦 موجودی شاپ با این گیفت کم نمی‌شود.\n\n"
            "برای نهایی‌کردن، تأیید کن.",
            reply_markup=confirmation_keyboard("shop"),
        )

    await callback.answer()


# ============================================================
# تأیید نهایی و ثبت مالکیت
# ============================================================

@router.callback_query(F.data.startswith("admin:gift:confirm:"))
async def confirm_gift(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    current_state = await state.get_state()

    if current_state != FanArtGiftStates.confirm_gift.state:
        await callback.answer(
            "این عملیات منقضی شده است. دوباره شروع کن.",
            show_alert=True,
        )
        return

    mode = callback.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    recipient_id = data.get("recipient_telegram_id")

    if (
        not recipient_id
        or data.get("gift_mode") != mode
        or mode not in {"direct", "shop"}
    ):
        await callback.answer(
            "اطلاعات عملیات ناقص یا نامعتبر است.",
            show_alert=True,
        )
        await state.clear()
        return

    if mode == "direct":
        required = ("image_file_id", "name", "description", "rarity")

        if any(key not in data for key in required):
            await callback.answer(
                "اطلاعات فن‌آرت ناقص است.",
                show_alert=True,
            )
            await state.clear()
            return

    elif not data.get("shop_fan_art_id"):
        await callback.answer(
            "فن‌آرت انتخاب نشده است.",
            show_alert=True,
        )
        await state.clear()
        return

    try:
        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == recipient_id
                )
            )

            if character is None:
                await callback.answer(
                    "پلیر دریافت‌کننده دیگر وجود ندارد.",
                    show_alert=True,
                )
                await state.clear()
                return

            if mode == "direct":
                fan_art = FanArt(
                    name=data["name"],
                    description=data["description"],
                    image_file_id=data["image_file_id"],
                    rarity=data["rarity"],
                    price=Decimal("0"),
                    is_active=False,
                    is_limited=False,
                    stock=None,
                    display_order=0,
                )

                session.add(fan_art)
                await session.flush()

            else:
                fan_art = await session.scalar(
                    select(FanArt).where(
                        FanArt.id == data["shop_fan_art_id"],
                        FanArt.is_active.is_(True),
                    )
                )

                if fan_art is None:
                    await callback.answer(
                        "فن‌آرت انتخابی دیگر فعال نیست.",
                        show_alert=True,
                    )
                    await state.clear()
                    return

                if fan_art.rarity != data.get("shop_rarity"):
                    await callback.answer(
                        "سطح فن‌آرت تغییر کرده است؛ دوباره انتخاب کن.",
                        show_alert=True,
                    )
                    await state.clear()
                    return

            existing_ownership = await session.scalar(
                select(FanArtOwnership.id)
                .where(
                    FanArtOwnership.telegram_id == recipient_id,
                    FanArtOwnership.fan_art_id == fan_art.id,
                )
                .limit(1)
            )

            if existing_ownership is not None:
                if mode == "direct":
                    await session.rollback()

                await callback.answer(
                    "این پلیر از قبل مالک این فن‌آرت است.",
                    show_alert=True,
                )
                await state.clear()
                return

            session.add(
                FanArtOwnership(
                    telegram_id=recipient_id,
                    fan_art_id=fan_art.id,
                    order_id=None,
                )
            )

            recipient_name = character.name
            fan_art_name = fan_art.name
            fan_art_image = fan_art.image_file_id
            fan_art_rarity = fan_art.rarity
            fan_art_description = fan_art.description
            saved_fan_art_id = fan_art.id

            await session.commit()

    except Exception:
        logger.exception("Failed to gift Fan Art")
        await callback.answer(
            "❌ خطا هنگام ثبت گیفت رخ داد. گزارش خطا را در ترمینال بررسی کن.",
            show_alert=True,
        )
        await state.clear()
        return

    await state.clear()

    notification_sent = False

    try:
        await callback.bot.send_photo(
            chat_id=recipient_id,
            photo=fan_art_image,
            caption=(
                "🎁 یک فن‌آرت جدید از طرف مدیریت دریافت کردی!\n\n"
                f"🎨 {fan_art_name}\n"
                f"💎 سطح: {rarity_name(fan_art_rarity)}\n"
                f"📖 {fan_art_description}\n\n"
                "این فن‌آرت به مجموعه فن‌آرت‌های تو اضافه شد."
            ),
        )
        notification_sent = True

    except Exception:
        logger.warning(
            "Could not send Fan Art photo notification to telegram_id=%s",
            recipient_id,
            exc_info=True,
        )

        try:
            await callback.bot.send_message(
                chat_id=recipient_id,
                text=(
                    "🎁 یک فن‌آرت جدید از طرف مدیریت دریافت کردی!\n\n"
                    f"🎨 {fan_art_name}\n"
                    f"💎 سطح: {rarity_name(fan_art_rarity)}\n\n"
                    "مالکیت فن‌آرت در حساب تو ثبت شده است."
                ),
            )
            notification_sent = True

        except Exception:
            logger.warning(
                "Could not send Fan Art text notification to telegram_id=%s",
                recipient_id,
                exc_info=True,
            )

    result_text = (
        "✅ گیفت در دیتابیس ثبت شد.\n\n"
        f"👤 پلیر: {recipient_name}\n"
        f"🎨 فن‌آرت: {fan_art_name}\n"
        f"💎 سطح: {rarity_name(fan_art_rarity)}\n"
        f"🆔 شناسه فن‌آرت: {saved_fan_art_id}\n"
        "💰 مبلغ دریافت‌شده از پلیر: ۰\n"
    )

    if notification_sent:
        result_text += "\n📨 پیام گیفت برای پلیر ارسال شد."
    else:
        result_text += (
            "\n⚠️ مالکیت ثبت شد، اما پیام به پلیر ارسال نشد. "
            "ممکن است پلیر هنوز ربات را شروع نکرده باشد."
        )

    if callback.message:
        await callback.message.edit_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🎁 مدیریت گیفت‌ها",
                            callback_data="admin:fanart_gifts",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🏠 پنل ادمین",
                            callback_data="admin:home",
                        )
                    ],
                ]
            ),
        )

    await callback.answer("🎁 گیفت ثبت شد.")


# ============================================================
# لغو عملیات
# ============================================================

@router.callback_query(F.data == "admin:gift:cancel")
async def cancel_gift(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎁 بازگشت به مدیریت گیفت",
                    callback_data="admin:fanart_gifts",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 پنل ادمین",
                    callback_data="admin:home",
                )
            ],
        ]
    )

    if callback.message:
        await callback.message.edit_text(
            "❌ عملیات گیفت لغو شد.",
            reply_markup=keyboard,
        )

    await callback.answer("عملیات لغو شد.")