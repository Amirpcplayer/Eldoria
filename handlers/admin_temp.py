from __future__ import annotations

import logging
import html
import random
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import delete, or_, select, func
from sqlalchemy.exc import SQLAlchemyError

from config.settings import settings
from bot.bot import bot
from database.database import AsyncSessionLocal
from models.character import Character
from models.fan_art import FanArtOwnership
from models.quest import CharacterQuest
from models.equipment import Equipment
from models.item import Item
from models.social_systems import Pet
from models.world_systems import MarketListing, GroupBoss, GroupBossContribution


router = Router()
logger = logging.getLogger(__name__)

PAGE_SIZE = 8
MAX_GOLD = 2_147_483_647


class AdminPlayerStates(StatesGroup):
    waiting_search = State()
    waiting_gold_search = State()
    waiting_gold_amount = State()


# مالک ثابت ربات، مستقل از عضویت در گروه‌ها
GLOBAL_BOT_OWNER_ID = 8537258392


def is_admin(telegram_id: int) -> bool:
    return telegram_id in (settings.admin_id, GLOBAL_BOT_OWNER_ID)


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎁 مدیریت گیفت فن‌آرت",
                    callback_data="admin:fanart_gifts",
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ افزودن فن‌آرت به شاپ",
                    callback_data="admin:fanart:add",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧾 سفارش‌های فن‌آرت",
                    callback_data="admin:fanart:orders",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 دادن گلد به پلیر",
                    callback_data="admin:gold:start",
                )
            ],
            [
                InlineKeyboardButton(text="✨ گیفت XP", callback_data="admin:resource_gift:xp"),
                InlineKeyboardButton(text="🔮 گیفت Skill XP", callback_data="admin:resource_gift:skill_xp"),
            ],
            [
                InlineKeyboardButton(text="💎 گیفت Gem", callback_data="admin:resource_gift:gems"),
            ],
            [
                InlineKeyboardButton(text="🐉 اسپان دستی باس", callback_data="admin:boss:spawn"),
            ],
            [
                InlineKeyboardButton(text="🌌 اسپان دستی دانجن", callback_data="admin:dungeon:spawn"),
            ],
            [
                InlineKeyboardButton(text="🎨 اسپان فن‌آرت", callback_data="admin:fanart:spawn"),
            ],
            [
                InlineKeyboardButton(text="✨ مدیریت ایموجی‌های پرمیوم", callback_data="admin:emoji:home"),
            ],
            [
                InlineKeyboardButton(text="🔎 جست‌وجوی بازیکن با یوزرنیم", callback_data="admin:players:search"),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 مدیریت پلیرها",
                    callback_data="admin:delete_players",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 فهرست پلیرها",
                    callback_data="admin:delete:list:0",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بستن پنل",
                    callback_data="admin:close",
                )
            ],
        ]
    )


def player_management_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔎 جست‌وجوی پلیر",
                    callback_data="admin:players:search",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 دادن گلد به پلیر",
                    callback_data="admin:gold:start",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 فهرست پلیرها",
                    callback_data="admin:delete:list:0",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به پنل ادمین",
                    callback_data="admin:home",
                )
            ],
        ]
    )


def player_list_keyboard(
    characters: list[Character],
    page: int,
    has_next: bool,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"👤 {character.name} · Lv.{character.level}",
                callback_data=f"admin:delete:select:{character.telegram_id}",
            )
        ]
        for character in characters
        if character.telegram_id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID)
    ]

    rows.insert(
        0,
        [
            InlineKeyboardButton(
                text="🔎 جست‌وجوی پلیر",
                callback_data="admin:players:search",
            )
        ],
    )

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ قبلی",
                callback_data=f"admin:delete:list:{page - 1}",
            )
        )

    if has_next:
        navigation.append(
            InlineKeyboardButton(
                text="بعدی ➡️",
                callback_data=f"admin:delete:list:{page + 1}",
            )
        )

    if navigation:
        rows.append(navigation)

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 مدیریت پلیرها",
                callback_data="admin:delete_players",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def player_details_keyboard(
    telegram_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 حذف این پلیر",
                    callback_data=f"admin:delete:confirm:{telegram_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔎 جست‌وجوی پلیر دیگر",
                    callback_data="admin:players:search",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 مدیریت پلیرها",
                    callback_data="admin:delete_players",
                )
            ],
        ]
    )


def player_search_results_keyboard(
    characters: list[Character],
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"👤 {character.name} · Lv.{character.level}",
                callback_data=f"admin:delete:select:{character.telegram_id}",
            )
        ]
        for character in characters
        if character.telegram_id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID)
    ]

    rows.append(
        [
            InlineKeyboardButton(
                text="🔎 جست‌وجوی دوباره",
                callback_data="admin:players:search",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 مدیریت پلیرها",
                callback_data="admin:delete_players",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


# در جست‌وجوی گلد، اکانت ادمین هم باید نمایش داده شود.
def gold_search_results_keyboard(
    characters: list[Character],
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=(
                    f"👤 {character.name} · "
                    f"Lv.{character.level} · 💰 {character.gold:,}"
                ),
                callback_data=f"admin:gold:select:{character.telegram_id}",
            )
        ]
        for character in characters
    ]

    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="🔎 جست‌وجوی دوباره",
                    callback_data="admin:gold:start",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 مدیریت پلیرها",
                    callback_data="admin:delete_players",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛡 پنل ادمین",
                    callback_data="admin:home",
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def gold_amount_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ لغو عملیات",
                    callback_data="admin:gold:cancel",
                )
            ]
        ]
    )


def gold_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید و واریز گلد",
                    callback_data="admin:gold:confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ تغییر مقدار",
                    callback_data="admin:gold:change",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو عملیات",
                    callback_data="admin:gold:cancel",
                )
            ],
        ]
    )


def admin_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛡 پنل ادمین",
                    callback_data="admin:home",
                )
            ]
        ]
    )


# ---------------------------------------------------------------------
# شناسه تلگرام
# ---------------------------------------------------------------------

@router.message(Command("myid"))
async def my_id_handler(message: Message):
    if message.from_user is None:
        return

    await message.answer(
        f"🆔 Telegram ID شما:\n\n{message.from_user.id}"
    )


# ---------------------------------------------------------------------
# پنل اصلی ادمین
# ---------------------------------------------------------------------

@router.message(Command("admin"))
async def admin_panel(
    message: Message,
    state: FSMContext,
):
    if message.from_user is None or not is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ادمین ندارید.")
        return

    await state.clear()

    await message.answer(
        "🛡 پنل مدیریت World Eldoria\n\n"
        "بخش موردنظرت را انتخاب کن:",
        reply_markup=admin_keyboard(),
    )


@router.callback_query(F.data == "admin:home")
async def admin_home_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "🛡 پنل مدیریت World Eldoria\n\n"
            "بخش موردنظرت را انتخاب کن:",
            reply_markup=admin_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "admin:close")
async def admin_close_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text("پنل مدیریت بسته شد.")

    await callback.answer()


@router.callback_query(F.data == "admin:delete_players")
async def delete_players_start(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "🗑 مدیریت پلیرها\n\n"
            "می‌توانی پلیر را جست‌وجو کنی یا فهرست پلیرها را ببینی.",
            reply_markup=player_management_keyboard(),
        )

    await callback.answer()


# ---------------------------------------------------------------------
# جست‌وجو و حذف پلیر
# ---------------------------------------------------------------------

@router.callback_query(F.data == "admin:players:search")
async def search_player_start(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminPlayerStates.waiting_search)

    if callback.message:
        await callback.message.answer(
            "🔎 جست‌وجوی پلیر\n\n"
            "یوزرنیم تلگرام یا Telegram ID پلیر را بفرست.\n\n"
            "مثال:\n"
            "@ExampleUser\n"
            "123456789\n\n"
            "برای لغو، /cancel را بفرست."
        )

    await callback.answer()


@router.message(Command("cancel"), AdminPlayerStates.waiting_search)
async def cancel_player_search(
    message: Message,
    state: FSMContext,
):
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return

    await state.clear()

    await message.answer(
        "جست‌وجو لغو شد.",
        reply_markup=player_management_keyboard(),
    )


@router.message(AdminPlayerStates.waiting_search)
async def search_player_submit(
    message: Message,
    state: FSMContext,
):
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text:
        await message.answer(
            "لطفاً یوزرنیم یا Telegram ID را به‌صورت متنی ارسال کن."
        )
        return

    query = message.text.strip()

    if not query:
        await message.answer("عبارت جست‌وجو خالی است.")
        return

    normalized_username = query.lstrip("@").strip().lower()

    conditions = [
        func.lower(Character.telegram_username) == normalized_username,
    ]

    if query.isdigit():
        conditions.append(Character.telegram_id == int(query))

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Character)
                .where(or_(*conditions))
                .order_by(Character.id.desc())
                .limit(10)
            )
            characters = list(result.scalars().all())

    except SQLAlchemyError:
        logger.exception(
            "Admin player search failed. Query=%r AdminID=%s",
            query,
            message.from_user.id,
        )
        await message.answer(
            "خطای پایگاه داده هنگام جست‌وجوی پلیر رخ داد. "
            "جزئیات در لاگ برنامه ثبت شد.",
            reply_markup=player_management_keyboard(),
        )
        return

    # جست‌وجوی عادی مدیریت، اکانت ادمین را مخفی نگه می‌دارد.
    characters = [
        character
        for character in characters
        if character.telegram_id not in (settings.admin_id, GLOBAL_BOT_OWNER_ID)
    ]

    if not characters:
        await message.answer(
            f"پلیر قابل مدیریتی با عبارت «{query}» پیدا نشد.",
            reply_markup=player_management_keyboard(),
        )
        return

    if len(characters) == 1:
        character = characters[0]

        await message.answer(
            "👤 پلیر پیدا شد\n\n"
            f"نام شخصیت: {character.name}\n"
            f"سطح: {character.level}\n"
            f"یوزرنیم: @{character.telegram_username or 'ثبت نشده'}\n"
            f"Telegram ID: {character.telegram_id}",
            reply_markup=player_details_keyboard(character.telegram_id),
        )
        return

    await message.answer(
        f"🔎 {len(characters)} نتیجه پیدا شد؛ پلیر موردنظر را انتخاب کن:",
        reply_markup=player_search_results_keyboard(characters),
    )


@router.callback_query(F.data.startswith("admin:delete:list:"))
async def delete_players_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    try:
        page = max(0, int(callback.data.rsplit(":", 1)[-1]))
    except (ValueError, AttributeError):
        await callback.answer("شماره صفحه نامعتبر است.", show_alert=True)
        return

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Character)
                .where(Character.telegram_id.not_in((settings.admin_id, GLOBAL_BOT_OWNER_ID)))
                .order_by(Character.id.desc())
                .offset(page * PAGE_SIZE)
                .limit(PAGE_SIZE + 1)
            )
            characters = list(result.scalars().all())

    except SQLAlchemyError:
        logger.exception(
            "Admin player listing failed. Page=%s AdminID=%s",
            page,
            callback.from_user.id,
        )
        await callback.answer(
            "خطای پایگاه داده؛ جزئیات در ترمینال ثبت شد.",
            show_alert=True,
        )
        return

    has_next = len(characters) > PAGE_SIZE
    characters = characters[:PAGE_SIZE]

    if not characters:
        await callback.answer(
            "پلیر دیگری در این صفحه نیست.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_text(
            "🗑 فهرست پلیرها\n\n"
            "پلیر موردنظر را انتخاب کن:",
            reply_markup=player_list_keyboard(
                characters,
                page,
                has_next,
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete:select:"))
async def delete_player_select(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    try:
        telegram_id = int(callback.data.rsplit(":", 1)[-1])
    except (ValueError, AttributeError):
        await callback.answer("شناسه پلیر نامعتبر است.", show_alert=True)
        return

    if telegram_id in (settings.admin_id, GLOBAL_BOT_OWNER_ID):
        await callback.answer(
            "حذف ادمین اصلی مجاز نیست.",
            show_alert=True,
        )
        return

    try:
        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == telegram_id
                )
            )

            if character is None:
                await callback.answer("پلیر پیدا نشد.", show_alert=True)
                return

            details = (
                "⚠️ اطلاعات پلیر\n\n"
                f"👤 نام شخصیت: {character.name}\n"
                f"📊 سطح: {character.level}\n"
                f"🆔 Telegram ID: {character.telegram_id}\n"
                f"🔎 یوزرنیم: "
                f"@{character.telegram_username or 'ثبت نشده'}\n\n"
                "برای حذف شخصیت و اطلاعات وابسته، تأیید را انتخاب کن."
            )

    except SQLAlchemyError:
        logger.exception(
            "Admin player details query failed. TelegramID=%s",
            telegram_id,
        )
        await callback.answer(
            "خطای پایگاه داده؛ جزئیات در ترمینال ثبت شد.",
            show_alert=True,
        )
        return

    if callback.message:
        await callback.message.edit_text(
            details,
            reply_markup=player_details_keyboard(telegram_id),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete:confirm:"))
async def delete_player_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    try:
        telegram_id = int(callback.data.rsplit(":", 1)[-1])
    except (ValueError, AttributeError):
        await callback.answer("شناسه پلیر نامعتبر است.", show_alert=True)
        return

    if telegram_id in (settings.admin_id, GLOBAL_BOT_OWNER_ID):
        await callback.answer(
            "حذف ادمین اصلی مجاز نیست.",
            show_alert=True,
        )
        return

    character_name: str | None = None
    deleted_quests = 0
    deleted_fan_art_ownerships = 0
    player_not_found = False

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                character = await session.scalar(
                    select(Character)
                    .where(Character.telegram_id == telegram_id)
                    .with_for_update()
                )

                if character is None:
                    player_not_found = True
                else:
                    character_name = character.name
                    character_id = character.id

                    ownership_result = await session.execute(
                        delete(FanArtOwnership).where(
                            FanArtOwnership.telegram_id == telegram_id
                        )
                    )
                    deleted_fan_art_ownerships = (
                        ownership_result.rowcount or 0
                    )

                    quest_result = await session.execute(
                        delete(CharacterQuest).where(
                            CharacterQuest.character_id == character_id
                        )
                    )
                    deleted_quests = quest_result.rowcount or 0

                    await session.execute(
                        delete(Character).where(
                            Character.id == character_id,
                            Character.telegram_id == telegram_id,
                        )
                    )

    except SQLAlchemyError as exc:
        logger.exception(
            "Failed to delete player: telegram_id=%s admin_id=%s "
            "error_type=%s error=%s",
            telegram_id,
            callback.from_user.id,
            type(exc).__name__,
            str(exc),
        )

        await callback.answer(
            "❌ حذف انجام نشد و تغییرات ذخیره نشدند. "
            "خطای پایگاه داده در ترمینال ثبت شد.",
            show_alert=True,
        )
        return

    except Exception:
        logger.exception(
            "Unexpected error deleting player. TelegramID=%s",
            telegram_id,
        )

        await callback.answer(
            "❌ هنگام حذف پلیر خطای غیرمنتظره‌ای رخ داد. "
            "جزئیات را در ترمینال بررسی کن.",
            show_alert=True,
        )
        return

    if player_not_found:
        await callback.answer(
            "این پلیر قبلاً حذف شده یا وجود ندارد.",
            show_alert=True,
        )
        return

    # Notify the player after the database deletion succeeds.
    try:
        await bot.send_message(
            telegram_id,
            "༺ ✦ اِلدوریا ✦ ༻\n\n"
            "حساب شما از طرف ادمین با موفقیت حذف شد.\n"
            "برای شروع دوباره /start بزنید.\n\n"
            "پشتیبانی : @P_ERSIAN19",
        )
    except Exception:
        # A blocked bot or a player who never opened the bot must not undo deletion.
        logger.warning(
            "Could not notify deleted player. telegram_id=%s",
            telegram_id,
            exc_info=True,
        )

    logger.info(
        "Player deleted by admin. telegram_id=%s admin_id=%s "
        "deleted_quests=%s deleted_fan_art_ownerships=%s",
        telegram_id,
        callback.from_user.id,
        deleted_quests,
        deleted_fan_art_ownerships,
    )

    if callback.message:
        await callback.message.edit_text(
            "✅ پلیر با موفقیت حذف شد.\n\n"
            f"👤 نام شخصیت: {character_name}\n"
            f"🆔 Telegram ID: {telegram_id}\n"
            f"📜 مأموریت‌های حذف‌شده: {deleted_quests}\n"
            f"🎨 مالکیت‌های فن‌آرت حذف‌شده: "
            f"{deleted_fan_art_ownerships}\n\n"
            "فن‌آرت‌های فروشگاه و سوابق سفارش‌ها حفظ شدند.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 مدیریت پلیرها",
                            callback_data="admin:delete_players",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🛡 پنل ادمین",
                            callback_data="admin:home",
                        )
                    ],
                ]
            ),
        )

    await callback.answer("پلیر با موفقیت حذف شد.")


# ---------------------------------------------------------------------
# دادن گلد به پلیر، شامل اکانت ادمین
# ---------------------------------------------------------------------

@router.callback_query(F.data == "admin:gold:start")
async def admin_gold_start(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminPlayerStates.waiting_gold_search)

    if callback.message:
        await callback.message.answer(
            "💰 دادن گلد به پلیر\n\n"
            "یوزرنیم یا Telegram ID بازیکن موردنظر را بفرست.\n\n"
            "اکانت خودت هم در این جست‌وجو قابل انتخاب است.\n\n"
            "مثال:\n"
            "@ExampleUser\n"
            "123456789\n\n"
            "برای لغو، /cancel را بفرست."
        )

    await callback.answer()


@router.message(
    Command("cancel"),
    AdminPlayerStates.waiting_gold_search,
)
@router.message(
    Command("cancel"),
    AdminPlayerStates.waiting_gold_amount,
)
async def admin_gold_cancel_message(
    message: Message,
    state: FSMContext,
):
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return

    await state.clear()

    await message.answer(
        "❌ عملیات دادن گلد لغو شد.",
        reply_markup=player_management_keyboard(),
    )


@router.message(AdminPlayerStates.waiting_gold_search)
async def admin_gold_search_submit(
    message: Message,
    state: FSMContext,
):
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text:
        await message.answer(
            "لطفاً یوزرنیم یا Telegram ID را به‌صورت متنی ارسال کن."
        )
        return

    query = message.text.strip()

    if not query:
        await message.answer("عبارت جست‌وجو خالی است.")
        return

    normalized_username = query.lstrip("@").strip().lower()

    conditions = [
        func.lower(Character.telegram_username) == normalized_username,
    ]

    if query.isdigit():
        conditions.append(Character.telegram_id == int(query))

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Character)
                .where(or_(*conditions))
                .order_by(Character.id.desc())
                .limit(10)
            )
            characters = list(result.scalars().all())

    except SQLAlchemyError:
        logger.exception(
            "Admin gold player search failed. Query=%r AdminID=%s",
            query,
            message.from_user.id,
        )
        await message.answer(
            "❌ هنگام جست‌وجوی بازیکن خطای پایگاه داده رخ داد. "
            "جزئیات در ترمینال ثبت شد.",
            reply_markup=player_management_keyboard(),
        )
        return

    # مهم: در جست‌وجوی گلد، اکانت ادمین را از نتایج حذف نمی‌کنیم.
    if not characters:
        await message.answer(
            f"بازیکنی با عبارت «{query}» پیدا نشد.\n"
            "می‌توانی دوباره جست‌وجو کنی.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔎 جست‌وجوی دوباره",
                            callback_data="admin:gold:start",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔙 مدیریت پلیرها",
                            callback_data="admin:delete_players",
                        )
                    ],
                ]
            ),
        )
        return

    await state.clear()

    if len(characters) == 1:
        character = characters[0]
        await show_gold_amount_prompt(
            message=message,
            state=state,
            telegram_id=character.telegram_id,
        )
        return

    await message.answer(
        f"🔎 {len(characters)} نتیجه پیدا شد.\n"
        "بازیکن موردنظر را انتخاب کن:",
        reply_markup=gold_search_results_keyboard(characters),
    )


async def show_gold_amount_prompt(
    message: Message,
    state: FSMContext,
    telegram_id: int,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == telegram_id
                )
            )

            # ادمین نیز می‌تواند مقصد دریافت گلد باشد.
            if character is None:
                await message.answer("بازیکن پیدا نشد یا حسابش حذف شده است.")
                return

            await state.update_data(gold_target_id=telegram_id)
            await state.set_state(AdminPlayerStates.waiting_gold_amount)

            await message.answer(
                "💰 تعیین مقدار گلد\n\n"
                f"👤 بازیکن: {character.name}\n"
                f"🆔 Telegram ID: {character.telegram_id}\n"
                f"💰 موجودی فعلی: {character.gold:,}\n\n"
                "مقدار گلدی را که می‌خواهی اضافه کنی، "
                "به‌صورت عدد صحیح مثبت بفرست.\n\n"
                "برای لغو، /cancel را بفرست.",
                reply_markup=gold_amount_keyboard(),
            )

    except SQLAlchemyError:
        logger.exception(
            "Failed to prepare admin gold transfer. TelegramID=%s",
            telegram_id,
        )
        await message.answer(
            "❌ دریافت اطلاعات بازیکن ناموفق بود. "
            "جزئیات در ترمینال ثبت شد."
        )


@router.callback_query(F.data.startswith("admin:gold:select:"))
async def admin_gold_select_player(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    try:
        telegram_id = int(callback.data.rsplit(":", 1)[-1])
    except (ValueError, AttributeError):
        await callback.answer("شناسه بازیکن نامعتبر است.", show_alert=True)
        return

    # اینجا عمداً اکانت ادمین مسدود نشده است.
    try:
        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == telegram_id
                )
            )

            if character is None:
                await callback.answer(
                    "بازیکن پیدا نشد یا حسابش حذف شده است.",
                    show_alert=True,
                )
                return

            await state.clear()
            await state.update_data(gold_target_id=telegram_id)
            await state.set_state(AdminPlayerStates.waiting_gold_amount)

            if callback.message:
                await callback.message.edit_text(
                    "💰 تعیین مقدار گلد\n\n"
                    f"👤 بازیکن: {character.name}\n"
                    f"🆔 Telegram ID: {character.telegram_id}\n"
                    f"💰 موجودی فعلی: {character.gold:,}\n\n"
                    "مقدار گلدی را که می‌خواهی اضافه کنی، "
                    "به‌صورت عدد صحیح مثبت بفرست.\n\n"
                    "برای لغو از دکمهٔ زیر استفاده کن.",
                    reply_markup=gold_amount_keyboard(),
                )

    except SQLAlchemyError:
        logger.exception(
            "Failed to select player for admin gold. TelegramID=%s",
            telegram_id,
        )
        await callback.answer(
            "خطای پایگاه داده رخ داد.",
            show_alert=True,
        )
        return

    await callback.answer()


@router.callback_query(F.data == "admin:gold:cancel")
async def admin_gold_cancel_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "❌ عملیات دادن گلد لغو شد.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 مدیریت پلیرها",
                            callback_data="admin:delete_players",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🛡 پنل ادمین",
                            callback_data="admin:home",
                        )
                    ],
                ]
            ),
        )

    await callback.answer("عملیات لغو شد.")


@router.message(AdminPlayerStates.waiting_gold_amount)
async def admin_gold_amount_submit(
    message: Message,
    state: FSMContext,
):
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text:
        await message.answer("مقدار گلد را به‌صورت عدد ارسال کن.")
        return

    raw_amount = message.text.strip().replace(",", "").replace("٬", "")

    if not raw_amount.isascii() or not raw_amount.isdigit():
        await message.answer(
            "❌ مقدار نامعتبر است.\n"
            "فقط یک عدد صحیح مثبت بفرست؛ مثلاً 5000."
        )
        return

    amount = int(raw_amount)

    if amount <= 0:
        await message.answer("❌ مقدار گلد باید بیشتر از صفر باشد.")
        return

    if amount > MAX_GOLD:
        await message.answer(
            "❌ مقدار واردشده بیش از حد مجاز است.\n"
            f"حداکثر مقدار هر واریز: {MAX_GOLD:,}"
        )
        return

    data = await state.get_data()
    telegram_id = data.get("gold_target_id")

    # مقصد می‌تواند اکانت ادمین باشد.
    if not isinstance(telegram_id, int):
        await state.clear()
        await message.answer(
            "❌ اطلاعات بازیکن معتبر نیست. لطفاً عملیات را از ابتدا شروع کن.",
            reply_markup=player_management_keyboard(),
        )
        return

    try:
        async with AsyncSessionLocal() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == telegram_id
                )
            )

            if character is None:
                await state.clear()
                await message.answer(
                    "❌ بازیکن پیدا نشد یا حسابش حذف شده است.",
                    reply_markup=player_management_keyboard(),
                )
                return

            if character.gold < 0 or character.gold + amount > MAX_GOLD:
                await message.answer(
                    "❌ موجودی نهایی از محدودهٔ مجاز دیتابیس خارج می‌شود.\n"
                    f"موجودی فعلی: {character.gold:,}\n"
                    f"مقدار درخواستی: {amount:,}"
                )
                return

            await state.update_data(gold_amount=amount)

            await message.answer(
                "⚠️ تأیید واریز گلد\n\n"
                f"👤 بازیکن: {character.name}\n"
                f"🆔 Telegram ID: {character.telegram_id}\n"
                f"💰 موجودی فعلی: {character.gold:,}\n"
                f"➕ گلد اهدایی: {amount:,}\n"
                f"💰 موجودی پس از واریز: {character.gold + amount:,}\n\n"
                "آیا واریز را تأیید می‌کنی؟",
                reply_markup=gold_confirmation_keyboard(),
            )

    except SQLAlchemyError:
        logger.exception(
            "Failed to prepare admin gold confirmation. TelegramID=%s",
            telegram_id,
        )
        await message.answer(
            "❌ خطای پایگاه داده رخ داد. جزئیات در ترمینال ثبت شد."
        )


@router.callback_query(F.data == "admin:gold:change")
async def admin_gold_change_amount(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    data = await state.get_data()
    telegram_id = data.get("gold_target_id")

    # مقصد ادمین هم معتبر است.
    if not isinstance(telegram_id, int):
        await state.clear()
        await callback.answer(
            "اطلاعات بازیکن منقضی شده است؛ دوباره شروع کن.",
            show_alert=True,
        )
        return

    await state.set_state(AdminPlayerStates.waiting_gold_amount)

    if callback.message:
        await callback.message.edit_text(
            "✏️ مقدار جدید گلد را به‌صورت عدد صحیح مثبت بفرست.\n\n"
            "برای لغو از دکمهٔ زیر استفاده کن.",
            reply_markup=gold_amount_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "admin:gold:confirm")
async def admin_gold_confirm(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    data = await state.get_data()
    telegram_id = data.get("gold_target_id")
    amount = data.get("gold_amount")

    # اکانت ادمین به‌عنوان مقصد مجاز است.
    if (
        not isinstance(telegram_id, int)
        or not isinstance(amount, int)
        or isinstance(amount, bool)
        or amount <= 0
        or amount > MAX_GOLD
    ):
        await state.clear()
        await callback.answer(
            "اطلاعات عملیات معتبر نیست؛ دوباره شروع کن.",
            show_alert=True,
        )
        return

    character_name: str | None = None
    old_gold: int | None = None
    new_gold: int | None = None
    failure_message: str | None = None

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                character = await session.scalar(
                    select(Character)
                    .where(Character.telegram_id == telegram_id)
                    .with_for_update()
                )

                if character is None:
                    failure_message = "بازیکن پیدا نشد یا حسابش حذف شده است."
                elif character.gold < 0:
                    failure_message = "موجودی فعلی بازیکن نامعتبر است."
                elif character.gold + amount > MAX_GOLD:
                    failure_message = (
                        "این واریز از حداکثر موجودی قابل ذخیره بیشتر است."
                    )
                else:
                    character_name = character.name
                    old_gold = character.gold
                    character.gold = old_gold + amount
                    new_gold = character.gold

    except SQLAlchemyError:
        logger.exception(
            "Admin gold transfer failed. target=%s admin=%s amount=%s",
            telegram_id,
            callback.from_user.id,
            amount,
        )
        await state.clear()
        await callback.answer(
            "❌ واریز انجام نشد؛ خطای دیتابیس در ترمینال ثبت شد.",
            show_alert=True,
        )
        return

    except Exception:
        logger.exception(
            "Unexpected error during admin gold transfer. target=%s",
            telegram_id,
        )
        await state.clear()
        await callback.answer(
            "❌ خطای غیرمنتظره هنگام واریز گلد.",
            show_alert=True,
        )
        return

    await state.clear()

    if failure_message:
        await callback.answer(failure_message, show_alert=True)

        if callback.message:
            await callback.message.edit_text(
                f"❌ واریز انجام نشد.\n\n{failure_message}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="💰 واریز گلد دیگر",
                                callback_data="admin:gold:start",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="🛡 پنل ادمین",
                                callback_data="admin:home",
                            )
                        ],
                    ]
                ),
            )
        return

    logger.info(
        "Admin gold granted. target_telegram_id=%s character=%s "
        "amount=%s old_gold=%s new_gold=%s admin_id=%s",
        telegram_id,
        character_name,
        amount,
        old_gold,
        new_gold,
        callback.from_user.id,
    )

    if callback.message:
        await callback.message.edit_text(
            "✅ گلد با موفقیت به بازیکن اضافه شد!\n\n"
            f"👤 بازیکن: {character_name}\n"
            f"🆔 Telegram ID: {telegram_id}\n"
            f"💰 موجودی قبلی: {old_gold:,}\n"
            f"➕ گلد اهدایی: {amount:,}\n"
            f"💰 موجودی جدید: {new_gold:,}\n\n"
            "تغییرات در دیتابیس ذخیره شد.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💰 واریز گلد دیگر",
                            callback_data="admin:gold:start",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔙 مدیریت پلیرها",
                            callback_data="admin:delete_players",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🛡 پنل ادمین",
                            callback_data="admin:home",
                        )
                    ],
                ]
            ),
        )

    await callback.answer("گلد با موفقیت واریز شد.")

@router.callback_query(F.data == "admin:overview")
async def admin_overview(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    try:
        async with AsyncSessionLocal() as session:
            players = await session.scalar(select(func.count(Character.id))) or 0
            gold = await session.scalar(select(func.coalesce(func.sum(Character.gold), 0))) or 0
            gems = await session.scalar(select(func.coalesce(func.sum(Character.gems), 0))) or 0
            equipment_count = await session.scalar(select(func.count(Equipment.id)).where(Equipment.is_active.is_(True))) or 0
            item_count = await session.scalar(select(func.count(Item.id))) or 0
            pets_count = await session.scalar(select(func.count(Pet.id)).where(Pet.is_active.is_(True))) or 0
            active_listings = await session.scalar(select(func.count(MarketListing.id)).where(MarketListing.status == "active")) or 0
        text = (
            "📊 <b>داشبورد جهان اِلدوریا</b>\n\n"
            f"👥 بازیکنان ثبت‌شده: <b>{players:,}</b>\n"
            f"💰 مجموع گلد بازیکنان: <b>{gold:,}</b>\n"
            f"💎 مجموع جم بازیکنان: <b>{gems:,}</b>\n"
            f"⚔️ تجهیزات فعال: <b>{equipment_count:,}</b>\n"
            f"📦 آیتم‌ها: <b>{item_count:,}</b>\n"
            f"🐾 پت‌های فعال: <b>{pets_count:,}</b>\n"
            f"🏪 آگهی‌های فعال بازار: <b>{active_listings:,}</b>\n\n"
            "عملیات حساس باید از بخش‌های مدیریتی و پس از بررسی شناسهٔ بازیکن انجام شود."
        )
        logger.info("Admin dashboard viewed by telegram_id=%s", callback.from_user.id)
    except SQLAlchemyError:
        logger.exception("Admin dashboard failed; admin_id=%s", callback.from_user.id)
        await callback.answer("خطا در خواندن آمار دیتابیس.", show_alert=True)
        return
    if callback.message:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💰 مدیریت گلد", callback_data="admin:gold:start")],
                [InlineKeyboardButton(text="👥 مدیریت بازیکنان", callback_data="admin:delete_players")],
                [InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="admin:home")],
            ]
        ))
    await callback.answer()


# -------------------- اسپان دستی باس --------------------
@router.callback_query(F.data == "admin:boss:spawn")
async def admin_boss_spawn_start(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی ندارید.", show_alert=True); return
    from handlers.group_boss import BOSS_POOL
    rows = []
    for i, cfg in enumerate(BOSS_POOL):
        rows.append([InlineKeyboardButton(text=cfg["name"][:55], callback_data=f"admin:boss:pick:{i}:0")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:home")])
    if cb.message:
        await cb.message.edit_text("🐉 باس موردنظر را انتخاب کن (۵۰ باس):", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows[:10] + [[InlineKeyboardButton(text="صفحه بعدی ➡️", callback_data="admin:boss:page:1")]] + rows[-1:]))
    await cb.answer()

@router.callback_query(F.data.startswith("admin:boss:page:"))
async def admin_boss_page(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی ندارید.", show_alert=True); return
    from handlers.group_boss import BOSS_POOL
    try: page=int((cb.data or "").rsplit(":",1)[1])
    except ValueError: page=0
    start=page*10; rows=[]
    for i,cfg in enumerate(BOSS_POOL[start:start+10], start):
        rows.append([InlineKeyboardButton(text=cfg["name"][:55], callback_data=f"admin:boss:pick:{i}:{page}")])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton(text="⬅️ قبلی",callback_data=f"admin:boss:page:{page-1}"))
    if start+10<len(BOSS_POOL): nav.append(InlineKeyboardButton(text="بعدی ➡️",callback_data=f"admin:boss:page:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 پنل ادمین",callback_data="admin:home")])
    if cb.message: await cb.message.edit_text("🐉 باس موردنظر را انتخاب کن:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await cb.answer()

@router.callback_query(F.data.startswith("admin:boss:pick:"))
async def admin_boss_pick(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی ندارید.", show_alert=True); return
    try: index=int((cb.data or "").split(":")[3])
    except (ValueError,IndexError): await cb.answer("انتخاب نامعتبر است.",show_alert=True); return
    from handlers.group_boss import BOSS_POOL
    if not 0 <= index < len(BOSS_POOL): await cb.answer("باس پیدا نشد.",show_alert=True); return
    cfg=BOSS_POOL[index]
    rows=[[InlineKeyboardButton(text=f"Lv.{level}",callback_data=f"admin:boss:level:{index}:{level}")] for level in (1,10,25,50,100,200)]
    rows.append([InlineKeyboardButton(text="🔙 انتخاب باس",callback_data="admin:boss:spawn")])
    if cb.message: await cb.message.edit_text(f"{cfg['name']}\nسطح باس را انتخاب کن:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await cb.answer()

@router.callback_query(F.data.startswith("admin:boss:level:"))
async def admin_boss_level(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی ندارید.", show_alert=True); return
    try: _,_,_,index,level=(cb.data or "").split(":",4); index=int(index); level=int(level)
    except ValueError: await cb.answer("انتخاب نامعتبر است.",show_alert=True); return
    async with AsyncSessionLocal() as session:
        groups=list((await session.scalars(select(GroupBoss).order_by(GroupBoss.chat_title))).all())
    # Refresh the displayed title from Telegram before rendering the destination picker.
    refreshed = {}
    for group in groups:
        try:
            live_chat = await bot.get_chat(group.chat_id)
            live_title = (live_chat.title or group.chat_title or str(group.chat_id))[:255]
            refreshed[group.chat_id] = live_title
        except Exception:
            refreshed[group.chat_id] = group.chat_title or str(group.chat_id)
    async with AsyncSessionLocal() as session:
        for group in groups:
            live_title = refreshed.get(group.chat_id)
            if live_title and group.chat_title != live_title:
                row = await session.scalar(select(GroupBoss).where(GroupBoss.chat_id == group.chat_id))
                if row:
                    row.chat_title = live_title
        await session.commit()
    rows=[]
    for group in groups:
        title=(refreshed.get(group.chat_id) or group.chat_title or str(group.chat_id))[:30]
        rows.append([InlineKeyboardButton(text=f"{title} · {group.chat_id}",callback_data=f"admin:boss:target:{index}:{level}:{group.chat_id}")])
    if not rows: rows=[[InlineKeyboardButton(text="گروهی ثبت نشده است",callback_data="admin:boss:spawn")]]
    rows.append([InlineKeyboardButton(text="🔙 پنل ادمین",callback_data="admin:home")])
    if cb.message: await cb.message.edit_text(f"باس سطح {level} انتخاب شد. گروه مقصد را انتخاب کن:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await cb.answer()

@router.callback_query(F.data.startswith("admin:boss:target:"))
async def admin_boss_target(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی ندارید.", show_alert=True); return
    try: _,_,_,index,level,chat_id=(cb.data or "").split(":",5); index=int(index); level=int(level); chat_id=int(chat_id)
    except ValueError: await cb.answer("انتخاب نامعتبر است.",show_alert=True); return
    from handlers.group_boss import BOSS_POOL, resolve_boss_image, boss_spawn_caption, boss_weakness
    if not 0 <= index < len(BOSS_POOL) or level not in (1,10,25,50,100,200): await cb.answer("انتخاب نامعتبر است.",show_alert=True); return
    cfg=BOSS_POOL[index]; now=datetime.utcnow()
    from handlers.group_boss import boss_level_stats
    async with AsyncSessionLocal() as session:
        group=await session.scalar(select(GroupBoss).where(GroupBoss.chat_id==chat_id).with_for_update())
        if not group: await cb.answer("گروه پیدا نشد؛ ابتدا ربات را به گروه اضافه کن.",show_alert=True); return
        if group.status=="active": await cb.answer("در این گروه باس فعالی وجود دارد. تا پایان آن صبر کن.",show_alert=True); return
        await session.execute(delete(GroupBossContribution).where(GroupBossContribution.boss_id==group.id))
        scaled_hp=min(2_000_000_000,boss_level_stats(cfg, level)["hp"])
        group.boss_key=cfg["key"]; group.boss_level=level; group.name=cfg["name"]
        group.max_hp=scaled_hp; group.hp=scaled_hp; group.status="active"; group.spawned_at=now; group.next_spawn_at=now+timedelta(hours=1); group.message_id=None
        await session.commit(); group_id=group.id; title=group.chat_title
    caption=boss_spawn_caption(cfg, level, scaled_hp, boss_weakness(cfg))
    image_path=resolve_boss_image(cfg)
    sent_photo = None
    sent_text = None
    try:
        from aiogram.types import FSInputFile
        if image_path is not None:
            # Send the artwork by itself, without a caption, so Telegram shows it fully.
            sent_photo = await bot.send_photo(chat_id, FSInputFile(str(image_path)))
            try:
                # Send the story template as a clean, independent message (no reply).
                sent_text = await bot.send_message(
                    chat_id,
                    caption,
                    parse_mode="HTML",
                )
            except Exception:
                try:
                    await bot.delete_message(chat_id, sent_photo.message_id)
                except Exception:
                    logger.debug("Could not remove orphaned manual boss photo", exc_info=True)
                raise
        else:
            sent_text = await bot.send_message(chat_id, caption, parse_mode="HTML")
    except Exception:
        async with AsyncSessionLocal() as session:
            group=await session.scalar(select(GroupBoss).where(GroupBoss.id==group_id))
            if group: group.status="waiting"; group.next_spawn_at=datetime.utcnow()+timedelta(minutes=5); await session.commit()
        logger.exception("Manual boss spawn failed for chat_id=%s",chat_id)
        await cb.answer("ارسال باس ناموفق بود؛ دسترسی ربات به گروه را بررسی کن.",show_alert=True); return
    async with AsyncSessionLocal() as session:
        group=await session.scalar(select(GroupBoss).where(GroupBoss.id==group_id))
        if group: group.message_id=sent_text.message_id; await session.commit()
    if cb.message: await cb.message.edit_text(f"✅ باس {cfg['name']} سطح {level} در گروه «{title}» ظاهر شد.")
    await cb.answer("باس با موفقیت اسپان شد.")


# -------------------- اسپان دستی فن‌آرت --------------------
@router.callback_query(F.data == "admin:fanart:spawn")
async def admin_fanart_spawn_start(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        groups = list((await session.scalars(select(GroupBoss).order_by(GroupBoss.chat_title))).all())
    rows = [[InlineKeyboardButton(text=f"{(g.chat_title or str(g.chat_id))[:30]} · {g.chat_id}", callback_data=f"admin:fanart:target:{g.chat_id}")] for g in groups]
    if not rows:
        rows = [[InlineKeyboardButton(text="هنوز گروهی ثبت نشده است", callback_data="admin:home")]]
    rows.append([InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="admin:home")])
    if cb.message:
        await cb.message.edit_text("🎨 گروه مقصد برای اسپان فن‌آرت را انتخاب کن:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await cb.answer()

@router.callback_query(F.data.startswith("admin:fanart:target:"))
async def admin_fanart_spawn_target(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    try:
        chat_id = int((cb.data or "").rsplit(":", 1)[1])
    except ValueError:
        await cb.answer("گروه نامعتبر است.", show_alert=True)
        return
    from handlers.fan_art_hunt import spawn_fan_art
    ok, message = await spawn_fan_art(chat_id, force=True)
    if cb.message:
        try:
            await cb.message.edit_text(("✅ " if ok else "❌ ") + message, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="admin:home")]]))
        except Exception:
            await cb.message.answer(("✅ " if ok else "❌ ") + message)
    await cb.answer("انجام شد." if ok else "اسپان ناموفق بود.", show_alert=not ok)
