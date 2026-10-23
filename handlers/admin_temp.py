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
from models.equipment import Equipment, CharacterEquipment
from models.item import Item
from models.inventory import Inventory
from models.fan_art import FanArt
from models.social_systems import Pet
from models.world_systems import MarketListing, GroupBoss, GroupBossContribution
from services.admin_permissions import add_delegated_admin, is_delegated_admin, list_delegated_admins, remove_delegated_admin


router = Router()
logger = logging.getLogger(__name__)

PAGE_SIZE = 8
MAX_GOLD = 2_147_483_647


class AdminPlayerStates(StatesGroup):
    waiting_search = State()
    waiting_gold_search = State()
    waiting_gold_amount = State()
    waiting_admin_username = State()


# مالک ثابت ربات، مستقل از عضویت در گروه‌ها
GLOBAL_BOT_OWNER_ID = 8537258392


def is_admin(telegram_id: int) -> bool:
    return telegram_id in (settings.admin_id, GLOBAL_BOT_OWNER_ID)


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ اضافه کردن ادمین",
                    callback_data="admin:admins:add",
                )
            ],
            [
                InlineKeyboardButton(
                    text="➖ برکناری ادمین",
                    callback_data="admin:admins:remove",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎨 مدیریت فن‌آرت شاپ",
                    callback_data="admin:fanart:manage",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎁 مدیریت گیفت فن‌آرت",
                    callback_data="admin:fanart_gifts",
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
                InlineKeyboardButton(text="📚 منوهای داخلی", callback_data="admin:internal_menu"),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 مدیریت پلیرها",
                    callback_data="admin:delete_players",
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




def delegated_admin_keyboard() -> InlineKeyboardMarkup:
    """Restricted panel containing only the delegated admin allowed sections."""
    keyboard = admin_keyboard()
    blocked = {
        "admin:admins:add",
        "admin:admins:remove",
        "admin:fanart_gifts",
        "admin:fanart:manage",
        "admin:fanart:add",
        "admin:fanart:orders",
        "admin:fanart:spawn",
    }
    rows = []
    for row in keyboard.inline_keyboard:
        visible = [button for button in row if button.callback_data not in blocked]
        if visible:
            rows.append(visible)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def fanart_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 مدیریت گیفت فن‌آرت", callback_data="admin:fanart_gifts")],
        [InlineKeyboardButton(text="➕ افزودن فن‌آرت به شاپ", callback_data="admin:fanart:add")],
        [InlineKeyboardButton(text="🧾 سفارش‌های فن‌آرت", callback_data="admin:fanart:orders")],
        [InlineKeyboardButton(text="🔙 بستن پنل", callback_data="admin:fanart:close")],
    ])


def player_management_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 لیست بازیکنان", callback_data="admin:players:list:0")],
        [InlineKeyboardButton(text="🔎 جست‌وجو با یوزرنیم تلگرام", callback_data="admin:players:search")],
        [InlineKeyboardButton(text="🔙 بازگشت به پنل ادمین", callback_data="admin:home")],
    ])


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
                callback_data=f"admin:profile:view:{character.telegram_id}",
            )
        ]
        for character in characters
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
    if message.from_user is None:
        return

    owner_access = is_admin(message.from_user.id)
    delegated_access = await is_delegated_admin(message.from_user.id)
    if not owner_access and not delegated_access:
        await message.answer("⛔ شما دسترسی ادمین ندارید.")
        return

    await state.clear()

    if message.chat.type != "private":
        bot_username = (await message.bot.get_me()).username
        if not bot_username:
            await message.answer("برای باز کردن پنل مدیریت، لطفاً ربات را در پی‌وی باز کن.")
            return
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="🔐 باز کردن پنل ادمین در پی‌وی",
                url=f"https://t.me/{bot_username}?start=admin",
            )
        ]])
        await message.answer(
            "🛡 پنل مدیریت فقط در گفت‌وگوی خصوصی باز می‌شود.\n\n"
            "روی دکمه بزن تا پی‌وی ربات باز شود و پنل ادمین خودکار نمایش داده شود.",
            reply_markup=markup,
        )
        return

    await state.clear()
    await message.answer(
        "🛡 پنل مدیریت World Eldoria\n\n"
        "بخش موردنظرت را انتخاب کن:",
        reply_markup=admin_keyboard() if owner_access else delegated_admin_keyboard(),
    )


INTERNAL_MENU_SECTIONS = [
    ("ادمین /admin", "internal:admin"),
    ("پروفایل", "internal:profile"),
    ("صندوقچه", "internal:inventory"),
    ("مهارت‌ها", "internal:skills"),
    ("تجهیزات", "internal:equipment"),
    ("ماموریت‌ها", "internal:quest"),
    ("ماجراجویی", "internal:adventure"),
    ("کرفتینگ", "internal:crafting"),
    ("پت", "internal:pets"),
    ("ایونت", "internal:events"),
    ("پارتی", "internal:party"),
    ("گیلد", "internal:guild"),
    ("رتبه‌بندی", "internal:ranking"),
    ("آهنگری", "internal:forge"),
    ("بازار بازیکنان", "internal:marketplace"),
    ("دفترچه هیولا", "internal:bestiary"),
    ("راهنما", "internal:guide"),
    ("تبدیل گلد به جم", "internal:gold_gems"),
    ("فروشگاه", "internal:shop"),
    ("تنظیمات", "internal:settings"),
]


def internal_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=callback_data)]
        for label, callback_data in INTERNAL_MENU_SECTIONS
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت به پنل ادمین", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "admin:internal_menu")
async def internal_menu_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ فقط مالک ربات به این بخش دسترسی دارد.", show_alert=True)
        return
    if callback.message:
        await callback.message.edit_text(
            "📚 <b>منوهای داخلی World Eldoria</b>\\n\\n"
            "بخش موردنظر را انتخاب کن. زیرساخت هر بخش در مراحل بعدی جداگانه ساخته می‌شود.",
            reply_markup=internal_menu_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("internal:"))
async def internal_menu_section_placeholder(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ فقط مالک ربات به این بخش دسترسی دارد.", show_alert=True)
        return
    selected = (callback.data or "").split(":", 1)[1]
    labels = dict((key.split(":", 1)[1], label) for label, key in INTERNAL_MENU_SECTIONS)
    if selected not in labels:
        await callback.answer("بخش نامعتبر است.", show_alert=True)
        return
    await callback.answer(f"«{labels[selected]}» هنوز ساخته نشده؛ مرحله‌به‌مرحله می‌سازیم.", show_alert=True)


@router.callback_query(F.data == "admin:fanart:close")
async def fanart_admin_close(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ فقط مالک ربات به بخش فن‌آرت دسترسی دارد.", show_alert=True)
        return
    await state.clear()
    if callback.message:
        await callback.message.edit_text("پنل مدیریت فن‌آرت بسته شد.")
    await callback.answer()


@router.callback_query(F.data == "admin:admins:add")
async def admin_add_delegated_admin_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ فقط مالک ربات می‌تواند ادمین اضافه کند.", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminPlayerStates.waiting_admin_username)
    if callback.message:
        await callback.message.answer(
            "➕ اضافه کردن ادمین\n\n"
            "یوزرنیم تلگرام بازیکن را بفرست؛ با یا بدون @.\n"
            "ادمین جدید فقط به دادن گلد، گیفت XP، گیفت Skill XP، گیفت Gem، اسپان دستی باس و دانجن، جست‌وجوی بازیکن، مدیریت پلیرها و فهرست پلیرها دسترسی خواهد داشت.\n"
            "تمام بخش‌های دیگر فقط برای مالک ربات باقی می‌ماند.\n\n"
            "لغو: /cancel"
        )
    await callback.answer()


@router.message(AdminPlayerStates.waiting_admin_username)
async def admin_add_delegated_admin_finish(message: Message, state: FSMContext):
    if message.from_user is None or not is_admin(message.from_user.id):
        await state.clear()
        return
    username = (message.text or "").strip().lstrip("@").lower()
    if username in {"", "cancel", "/cancel"}:
        await state.clear()
        await message.answer("عملیات افزودن ادمین لغو شد.", reply_markup=admin_keyboard())
        return
    async with AsyncSessionLocal() as session:
        target = await session.scalar(
            select(Character).where(func.lower(Character.telegram_username) == username)
        )
    if target is None:
        await message.answer(
            "❌ این یوزرنیم در بازیکنان ثبت‌شده پیدا نشد.\n"
            "بازیکن باید ابتدا ربات را باز کرده و /start زده باشد؛ سپس دوباره تلاش کن."
        )
        return
    if is_admin(target.telegram_id):
        await state.clear()
        await message.answer("این حساب از قبل مالک اصلی ربات است.", reply_markup=admin_keyboard())
        return
    await add_delegated_admin(target.telegram_id)
    await state.clear()

    # Notify the newly appointed admin privately. Failure to deliver the DM
    # must not undo the permission change.
    try:
        await bot.send_message(
            target.telegram_id,
            "╭─── ✦ 🛡️ ✦ ───╮\n"
            "   <b>خوش‌آمدید، ادمین محترم اِلدوریا</b>\n"
            "╰─── ✦ 🛡️ ✦ ───╯\n\n"
            "با احترام، به جمع مدیران منتخب <b>World Eldoria</b> خوش آمدید. ✨\n"
            "مالک ربات به شما اعتماد کرده و دسترسی مدیریتی محدود و مشخصی در اختیارتان قرار داده است.\n\n"
            "🔑 <b>دسترسی‌های شما</b>\n"
            "• دادن گلد به بازیکنان\n"
            "• گیفت XP، Skill XP و Gem\n"
            "• اسپان دستی باس و دانجن\n"
            "• جست‌وجوی بازیکنان، مدیریت پلیرها و مشاهده فهرست آن‌ها\n\n"
            "لطفاً با دقت، انصاف و احترام از این دسترسی‌ها استفاده کنید. سایر بخش‌های مدیریتی همچنان در اختیار مالک ربات است.\n\n"
            "برای ورود به پنل، به پی‌وی ربات برگردید و دستور /admin را ارسال کنید.\n\n"
            "🌟 از همراهی و مسئولیت‌پذیری شما سپاسگزاریم.\n"
            "<i>تیم World Eldoria</i>",
            parse_mode="HTML",
        )
    except Exception:
        logger.warning("Could not DM newly appointed delegated admin telegram_id=%s", target.telegram_id, exc_info=True)

    await message.answer(
        "✅ ادمین با موفقیت اضافه شد.\n\n"
        f"👤 @{target.telegram_username or username}\n"
        f"🆔 {target.telegram_id}\n\n"
        "پیام خوش‌آمدگویی و توضیحات دسترسی نیز در صورت امکان به پی‌وی او ارسال شد.",
        reply_markup=admin_keyboard(),
    )


@router.callback_query(F.data == "admin:admins:remove")
async def admin_remove_delegated_admin_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ فقط مالک ربات می‌تواند ادمین برکنار کند.", show_alert=True)
        return

    admin_ids = await list_delegated_admins()
    buttons = []
    async with AsyncSessionLocal() as session:
        for telegram_id in admin_ids:
            player = await session.scalar(
                select(Character).where(Character.telegram_id == telegram_id)
            )
            username = (getattr(player, "telegram_username", None) or "").strip().lstrip("@")
            label = f"@{username}" if username else f"شناسه {telegram_id}"
            buttons.append([
                InlineKeyboardButton(
                    text=f"➖ {label}",
                    callback_data=f"admin:admins:remove:{telegram_id}",
                )
            ])

    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:home")])
    text = "➖ برکناری ادمین\n\n"
    if admin_ids:
        text += "روی ادمینی که می‌خواهی دسترسی‌اش لغو شود بزن:"
    else:
        text += "در حال حاضر هیچ ادمین اضافه‌شده‌ای وجود ندارد."
    if callback.message:
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:admins:remove:"))
async def admin_remove_delegated_admin_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ فقط مالک ربات می‌تواند ادمین برکنار کند.", show_alert=True)
        return

    try:
        target_id = int((callback.data or "").rsplit(":", 1)[1])
    except (TypeError, ValueError):
        await callback.answer("شناسه ادمین معتبر نیست.", show_alert=True)
        return

    if is_admin(target_id):
        await callback.answer("مالک اصلی ربات قابل برکناری نیست.", show_alert=True)
        return

    if not await is_delegated_admin(target_id):
        await callback.answer("این حساب دیگر ادمین نیست.", show_alert=True)
        return

    await remove_delegated_admin(target_id)

    # Notify the former admin privately. Revocation remains successful even
    # if Telegram does not allow the bot to deliver a private message.
    try:
        async with AsyncSessionLocal() as session:
            target = await session.scalar(
                select(Character).where(Character.telegram_id == target_id)
            )
        username = (getattr(target, "telegram_username", None) or "").strip().lstrip("@")
        identity = f"@{username}" if username else f"شناسه تلگرام: {target_id}"
        await bot.send_message(
            target_id,
            "╭─── ✦ 📜 ✦ ───╮\n"
            "   <b>اطلاعیه محترمانه مدیریت اِلدوریا</b>\n"
            "╰─── ✦ 📜 ✦ ───╯\n\n"
            "ادمین گرامی،\n"
            "با احترام به اطلاع می‌رسانیم که دسترسی مدیریتی شما در <b>World Eldoria</b> بنا به تصمیم مالک ربات لغو شده است.\n\n"
            "از زمانی که برای همراهی و کمک به مدیریت اِلدوریا گذاشتید، صمیمانه سپاسگزاریم. این تغییر صرفاً به معنی پایان دسترسی مدیریتی است و از احترام ما به شما کم نمی‌کند. 🤝\n\n"
            "از این پس امکان استفاده از پنل و ابزارهای مدیریتی برای شما فعال نخواهد بود. همچنان می‌توانید مانند سایر بازیکنان از دنیای اِلدوریا لذت ببرید.\n\n"
            "برای شما روزهایی خوش و ماجراجویی‌هایی درخشان آرزو می‌کنیم. ✨\n\n"
            "<i>با احترام، تیم World Eldoria</i>",
            parse_mode="HTML",
        )
    except Exception:
        logger.warning("Could not DM removed delegated admin telegram_id=%s", target_id, exc_info=True)

    await admin_remove_delegated_admin_list(callback)


@router.callback_query(F.data == "admin:home")
async def admin_home_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "🛡 پنل مدیریت World Eldoria\n\n"
            "بخش موردنظرت را انتخاب کن:",
            reply_markup=admin_keyboard() if is_admin(callback.from_user.id) else delegated_admin_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "admin:close")
async def admin_close_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "🗑 مدیریت پلیرها\n\n"
            "از اینجا می‌توانی لیست بازیکنان را باز کنی یا با یوزرنیم تلگرام، مستقیم پروفایل یک بازیکن را ببینی.",
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
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
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
    if message.from_user is None or (not is_admin(message.from_user.id) and not await is_delegated_admin(message.from_user.id)):
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
    if message.from_user is None or (not is_admin(message.from_user.id) and not await is_delegated_admin(message.from_user.id)):
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

    if not characters:
        await message.answer(
            f"پلیر قابل مدیریتی با عبارت «{query}» پیدا نشد.",
            reply_markup=player_management_keyboard(),
        )
        return

    if len(characters) == 1:
        character = characters[0]
        await state.clear()
        await message.answer(
            f"👤 بازیکن «{character.name}» پیدا شد. برای مشاهده پروفایل کامل، تجهیزات، آیتم‌ها و فن‌آرت‌ها روی دکمه زیر بزن.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 مشاهده پروفایل کامل", callback_data=f"admin:profile:view:{character.telegram_id}")],
                [InlineKeyboardButton(text="🔎 جست‌وجوی دوباره", callback_data="admin:players:search")],
            ]),
        )
        return

    await message.answer(
        f"🔎 {len(characters)} نتیجه پیدا شد؛ پلیر موردنظر را انتخاب کن:",
        reply_markup=player_search_results_keyboard(characters),
    )


@router.callback_query(F.data.startswith("admin:players:list:"))
async def admin_players_list_alias(callback: CallbackQuery):
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    try:
        page = max(0, int((callback.data or "").rsplit(":", 1)[-1]))
    except (ValueError, AttributeError):
        await callback.answer("شماره صفحه نامعتبر است.", show_alert=True)
        return
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Character)
                .order_by(Character.id.desc())
                .offset(page * PAGE_SIZE)
                .limit(PAGE_SIZE + 1)
            )
            characters = list(result.scalars().all())
    except SQLAlchemyError:
        logger.exception("Admin player listing failed. Page=%s AdminID=%s", page, callback.from_user.id)
        await callback.answer("خطای پایگاه داده؛ جزئیات در ترمینال ثبت شد.", show_alert=True)
        return
    has_next = len(characters) > PAGE_SIZE
    characters = characters[:PAGE_SIZE]
    if not characters:
        if callback.message:
            await callback.message.edit_text("📚 در این صفحه بازیکنی برای نمایش وجود ندارد.", reply_markup=player_management_keyboard())
        await callback.answer()
        return
    rows = [[InlineKeyboardButton(
        text=f"👤 {c.name} · Lv.{c.level}",
        callback_data=f"admin:profile:view:{c.telegram_id}",
    )] for c in characters]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"admin:players:list:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="بعدی ➡️", callback_data=f"admin:players:list:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔎 جست‌وجو با یوزرنیم", callback_data="admin:players:search")])
    rows.append([InlineKeyboardButton(text="🔙 مدیریت پلیرها", callback_data="admin:delete_players")])
    if callback.message:
        await callback.message.edit_text(
            f"📚 <b>لیست بازیکنان</b> · صفحه {page + 1}\n\nبازیکن موردنظر را انتخاب کن تا پروفایل و دارایی‌هایش نمایش داده شود.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:profile:view:"))
async def admin_player_profile_view(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return
    await state.clear()
    try:
        telegram_id = int((callback.data or "").rsplit(":", 1)[1])
    except (TypeError, ValueError):
        await callback.answer("شناسه بازیکن معتبر نیست.", show_alert=True)
        return
    try:
        async with AsyncSessionLocal() as session:
            character = await session.scalar(select(Character).where(Character.telegram_id == telegram_id))
            if character is None:
                await callback.answer("بازیکن پیدا نشد.", show_alert=True)
                return
            equipment_rows = (await session.execute(
                select(Equipment.name, CharacterEquipment.quantity, CharacterEquipment.equipped, CharacterEquipment.enhancement_level)
                .join(CharacterEquipment, CharacterEquipment.equipment_id == Equipment.id)
                .where(CharacterEquipment.character_id == character.id)
                .order_by(CharacterEquipment.equipped.desc(), Equipment.name)
            )).all()
            item_rows = (await session.execute(
                select(Item.name, Inventory.quantity)
                .join(Inventory, Inventory.item_id == Item.id)
                .where(Inventory.character_id == character.id)
                .order_by(Item.name)
            )).all()
            fan_art_rows = (await session.execute(
                select(FanArt.name)
                .join(FanArtOwnership, FanArtOwnership.fan_art_id == FanArt.id)
                .where(FanArtOwnership.telegram_id == telegram_id)
                .order_by(FanArt.name)
            )).all()
        equipment_text = [f"{'🛡️' if equipped else '🎒'} {name} ×{quantity}" + (f" · +{enhancement}" if enhancement else "") for name, quantity, equipped, enhancement in equipment_rows]
        items_text = [f"📦 {name} ×{quantity}" for name, quantity in item_rows]
        fan_art_text = [f"🎨 {name}" for (name,) in fan_art_rows]
        profile = (
            "╭─── ✦ 👤 ✦ ───╮\n"
            f"  <b>پروفایل بازیکن · {html.escape(character.name)}</b>\n"
            "╰─── ✦ 👤 ✦ ───╯\n\n"
            f"🔎 یوزرنیم: @{html.escape(character.telegram_username or 'ثبت نشده')}\n"
            f"🆔 شناسه: <code>{telegram_id}</code>\n"
            f"🧬 نژاد: {html.escape(character.race or 'نامشخص')}\n"
            f"⭐ سطح: {character.level} · ✨ XP: {int(character.xp or 0):,}\n"
            f"🔮 Skill XP: {int(character.skill_xp or 0):,}\n"
            f"💰 گلد: {int(character.gold or 0):,} · 💎 جم: {int(character.gems or 0):,}\n"
            f"❤️ HP: {character.hp:,}/{character.max_hp:,} · 💧 مانا: {character.mana:,}/{character.max_mana:,}\n"
            f"⚔️ حمله: {character.attack:,} · 🛡 دفاع: {character.defense:,}\n\n"
            "<b>🛡️ تجهیزات</b>\n" + ("\n".join(equipment_text) if equipment_text else "تجهیزاتی ثبت نشده") + "\n\n"
            "<b>📦 صندوقچه و آیتم‌ها</b>\n" + ("\n".join(items_text) if items_text else "آیتمی ثبت نشده") + "\n\n"
            "<b>🎨 فن‌آرت‌ها</b>\n" + ("\n".join(fan_art_text) if fan_art_text else "فن‌آرتی ندارد")
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔎 جست‌وجوی بازیکن دیگر", callback_data="admin:players:search")],
            [InlineKeyboardButton(text="📚 بازگشت به لیست بازیکنان", callback_data="admin:players:list:0")],
            [InlineKeyboardButton(text="🗑 حذف بازیکن", callback_data=f"admin:delete:select:{telegram_id}")],
            [InlineKeyboardButton(text="🔙 مدیریت پلیرها", callback_data="admin:delete_players")],
        ])
        if callback.message:
            await callback.message.edit_text(profile, parse_mode="HTML", reply_markup=markup)
    except SQLAlchemyError:
        logger.exception("Admin profile view failed for telegram_id=%s", telegram_id)
        await callback.answer("خطای پایگاه داده هنگام خواندن پروفایل.", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete:list:"))
async def delete_players_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
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
            "╭─── ✦ ⚔️ ✦ ───╮\n"
            "   <b>پیامی از دنیای اِلدوریا</b>\n"
            "╰─── ✦ ⚔️ ✦ ───╯\n\n"
            "قهرمان عزیز، شخصیت و حساب بازی شما توسط مدیریت حذف شده است.\n\n"
            "🌱 اگر می‌خواهید ماجراجویی تازه‌ای آغاز کنید، دکمهٔ «شروع دوباره» را بزنید تا شخصیت جدیدتان را بسازید.\n\n"
            "📨 اگر فکر می‌کنید حساب شما به اشتباه حذف شده، برای بررسی موضوع با پشتیبانی در ارتباط باشید:\n"
            "👤 @P_ERSIAN19\n\n"
            "✨ دروازه‌های اِلدوریا برای آغاز دوباره باز هستند.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ شروع دوباره و ساخت شخصیت", url="https://t.me/WorldEldoriaBot?start=restart")],
                [InlineKeyboardButton(text="📨 ارتباط با پشتیبانی", url="https://t.me/P_ERSIAN19")],
            ]),
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
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
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
    if message.from_user is None or (not is_admin(message.from_user.id) and not await is_delegated_admin(message.from_user.id)):
        await state.clear()
        return

    await state.clear()

    await message.answer(
        "🛡 پنل مدیریت World Eldoria\n\nعملیات واریز گلد لغو شد؛ به منوی اصلی برگشتی.",
        reply_markup=admin_keyboard() if is_admin(message.from_user.id) else delegated_admin_keyboard(),
    )


@router.message(AdminPlayerStates.waiting_gold_search)
async def admin_gold_search_submit(
    message: Message,
    state: FSMContext,
):
    if message.from_user is None or (not is_admin(message.from_user.id) and not await is_delegated_admin(message.from_user.id)):
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
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "🛡 <b>پنل مدیریت World Eldoria</b>\\n\\nعملیات واریز گلد لغو شد؛ به منوی اصلی برگشتی.",
            parse_mode="HTML",
            reply_markup=admin_keyboard() if is_admin(callback.from_user.id) else delegated_admin_keyboard(),
        )

    await callback.answer("عملیات لغو شد.")


@router.message(AdminPlayerStates.waiting_gold_amount)
async def admin_gold_amount_submit(
    message: Message,
    state: FSMContext,
):
    if message.from_user is None or (not is_admin(message.from_user.id) and not await is_delegated_admin(message.from_user.id)):
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
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id) and not await is_delegated_admin(callback.from_user.id):
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

    try:
        await bot.send_message(
            telegram_id,
            "╭─── ✦ 💰 ✦ ───╮\n"
            "   <b>هدیه‌ای از سوی مدیریت اِلدوریا</b>\n"
            "╰─── ✦ 💰 ✦ ───╯\n\n"
            f"قهرمان <b>{html.escape(character_name or 'اِلدوریا')}</b>، خبر خوش! ✨\n"
            "مدیریت World Eldoria برای قدردانی از حضورت، این هدیه را به حسابت اضافه کرد.\n\n"
            f"🎁 گلد دریافتی: <b>+{amount:,}</b>\n"
            f"💰 موجودی جدید: <b>{new_gold:,}</b>\n\n"
            "امیدواریم این هدیه در ماجراجویی‌های بعدی همراهت باشد.\n"
            "<i>با آرزوی درخشش بیشتر، تیم World Eldoria</i>",
            parse_mode="HTML",
        )
    except Exception:
        logger.info("Could not DM gold gift recipient telegram_id=%s", telegram_id, exc_info=True)

    if callback.message:
        await callback.message.edit_text(
            "╭─── ✦ 🧾 ✦ ───╮\n"
            "   <b>فاکتور واریز گلد</b>\n"
            "╰─── ✦ 🧾 ✦ ───╯\n\n"
            f"👤 بازیکن: <b>{html.escape(character_name or 'نامشخص')}</b>\n"
            f"🆔 Telegram ID: <code>{telegram_id}</code>\n"
            f"💰 موجودی قبلی: <b>{old_gold:,}</b>\n"
            f"➕ گلد واریزشده: <b>{amount:,}</b>\n"
            f"💰 موجودی جدید: <b>{new_gold:,}</b>\n"
            f"🛡 انجام‌دهنده: <code>{callback.from_user.id}</code>\n"
            "📌 وضعیت: <b>موفق</b>\n\n"
            "رسید این عملیات ثبت شد.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 واریز گلد دیگر", callback_data="admin:gold:start")],
                [InlineKeyboardButton(text="🛡 پنل ادمین", callback_data="admin:home")],
            ]),
        )

    await callback.answer("گلد با موفقیت واریز شد.")

@router.callback_query(F.data == "admin:overview")
async def admin_overview(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ این بخش فقط برای مالک ربات است.", show_alert=True)
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
    if not is_admin(cb.from_user.id) and not await is_delegated_admin(cb.from_user.id):
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
    if not is_admin(cb.from_user.id) and not await is_delegated_admin(cb.from_user.id):
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
    if not is_admin(cb.from_user.id) and not await is_delegated_admin(cb.from_user.id):
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
    if not is_admin(cb.from_user.id) and not await is_delegated_admin(cb.from_user.id):
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
    if not is_admin(cb.from_user.id) and not await is_delegated_admin(cb.from_user.id):
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
        group.max_hp=scaled_hp; group.hp=scaled_hp; group.status="active"; group.spawned_at=now; group.next_spawn_at=now+timedelta(hours=12); group.message_id=None
        await session.commit(); group_id=group.id; title=group.chat_title
    caption=boss_spawn_caption(cfg, level, scaled_hp, boss_weakness(cfg))
    image_path=resolve_boss_image(cfg)
    sent_photo = None
    sent_text = None
    try:
        from aiogram.types import FSInputFile
        if image_path is not None:
            # Restore the original single-message presentation: boss image with story caption.
            sent_photo = await bot.send_photo(
                chat_id,
                FSInputFile(str(image_path)),
                caption=caption,
                parse_mode="HTML",
            )
            sent_text = sent_photo
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
        await cb.answer("⛔ اسپان فن‌آرت فقط برای مالک ربات است.", show_alert=True)
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
        await cb.answer("⛔ اسپان فن‌آرت فقط برای مالک ربات است.", show_alert=True)
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
