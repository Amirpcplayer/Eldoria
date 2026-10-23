from __future__ import annotations

import logging
import html
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.fan_art import FanArt

from middlewares.panel_owner import protect_keyboard

from services.fan_art_service import (
    clear_active_fan_art,
    get_active_fan_art,
    get_owned_fan_arts,
    set_active_fan_art,
)

from services.equipment_service import get_final_character_stats
from services.character_stats_service import (
    calculate_character_combat_stats,
    calculate_character_base_stats,
)
from services.xp_service import (
    get_required_xp,
    MAX_CHARACTER_LEVEL,
)
from services.title_service import TITLES, sync_unlocked_titles, title_for_level
from services.vitals_recovery_service import recover_character_vitals
from models.social_systems import Guild, GuildMember, Party, PartyMember
from services.scroll_service import active_buffs, SCROLLS
from services.language_service import get_language, tr


router = Router()
logger = logging.getLogger(__name__)


# ============================================================
# XP PROGRESS BAR
# ============================================================

def build_xp_progress_bar(
    level: int,
    xp: int,
) -> str:
    """ساخت نوار XP با نمادهای متنی ساده و فرمول اصلی سیستم تجربه."""
    level = max(1, int(level or 1))
    xp = max(0, int(xp or 0))
    width = 10

    if level >= MAX_CHARACTER_LEVEL:
        return (
            f"└ تجربه فعلی: {xp:,} XP\n"
            "└ وضعیت: حداکثر سطح اِلدوریا 👑\n"
            + "▰" * width
            + " 100٪"
        )

    required_xp = max(0, int(get_required_xp(level) or 0))
    if required_xp <= 0:
        return (
            f"└ تجربه فعلی: {xp:,} XP\n"
            "└ XP موردنیاز سطح بعدی: ۰\n"
            + "▰" * width
            + " 100٪"
        )

    current_xp = min(xp, required_xp)
    percentage = min(100, int(current_xp * 100 / required_xp))
    filled = min(width, int(current_xp * width / required_xp))
    bar = "▰" * filled + "▱" * (width - filled)
    remaining = max(0, required_xp - current_xp)

    return (
        f"└ تجربه فعلی: {xp:,} XP\n"
        f"└ سطح بعدی: {required_xp:,} XP\n"
        f"└ باقی‌مانده: {remaining:,} XP\n"
        f"{bar} {percentage}٪"
    )


# ============================================================
# KEYBOARDS
# ============================================================

def profile_keyboard(language: str = "fa") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=tr(language, "inventory"),
                    callback_data="menu:inventory",
                ),
                InlineKeyboardButton(
                    text=tr(language, "equipment"),
                    callback_data="menu:equipment",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(language, "skills"),
                    callback_data="menu:skills",
                ),
                InlineKeyboardButton(
                    text="آمار کامل پروفایل",
                    callback_data="profile:stats",
                ),
            ],
            [
                InlineKeyboardButton(text="بازیابی سلامت", callback_data="potion:choose:hp"),
                InlineKeyboardButton(text="بازیابی مانا", callback_data="potion:choose:mana"),
            ],
            [
                InlineKeyboardButton(
                    text="لقب‌ها",
                    callback_data="profile:titles",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="انتخاب فن‌آرت",
                    callback_data="profile:fanart",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(language, "back"),
                    callback_data="menu:back",
                ),
            ],
        ]
    )


def profile_fan_art_keyboard(
    fan_arts: list[FanArt],
    active_fan_art_id: int | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for fan_art in fan_arts:
        text = (
            f"✅ {fan_art.name}"
            if fan_art.id == active_fan_art_id
            else f"🎨 {fan_art.name}"
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"profile:setfanart:{fan_art.id}",
                )
            ]
        )

    if active_fan_art_id is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚫 حذف Fan Art فعال",
                    callback_data="profile:clearfanart",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت به پروفایل",
                callback_data="menu:profile",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def title_keyboard(unlocked: list[int], active_title: str | None, page: int = 0) -> InlineKeyboardMarkup:
    page_size = 10
    pages = max(1, (len(unlocked) + page_size - 1) // page_size)
    page = max(0, min(page, pages - 1))
    rows: list[list[InlineKeyboardButton]] = []
    for level in unlocked[page * page_size:(page + 1) * page_size]:
        title = TITLES[level - 1]
        prefix = "✅ " if title == active_title else "🎖️ "
        rows.append([InlineKeyboardButton(text=f"{prefix}Lv.{level} — {title}", callback_data=f"profile:settitle:{level}")])
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"profile:titlepage:{page - 1}"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton(text="بعدی ➡️", callback_data=f"profile:titlepage:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 بازگشت به پروفایل", callback_data="menu:profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def render_titles(callback: CallbackQuery, page: int = 0) -> None:
    telegram_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == telegram_id))
        if character is None:
            await callback.answer("❌ قهرمان پیدا نشد.", show_alert=True)
            return
        unlocked = sync_unlocked_titles(character)
        active_title = character.active_title
        character_name = character.name
        level = character.level
        await session.commit()
    text = (
        "🏰 <b>تالار القاب اِلدوریا</b>\n\n"
        f"🧙 قهرمان: {character_name}\n⭐ سطح فعلی: {level}\n"
        f"🎖️ لقب فعال: <b>{active_title}</b>\n\n"
        f"🔓 لقب‌های بازشده: {len(unlocked)}/100\n"
        "با هر سطح جدید، لقب مخصوص همان سطح باز می‌شود. یکی از لقب‌های بازشده را انتخاب کن:"
    )
    markup = owned_keyboard(title_keyboard(unlocked, active_title, page), telegram_id)
    if callback.message is not None:
        try:
            await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
        except Exception:
            await callback.message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)


def owned_keyboard(
    keyboard: InlineKeyboardMarkup,
    telegram_id: int,
) -> InlineKeyboardMarkup:
    """اختصاص تمام دکمه‌های یک کیبورد به صاحب پنل."""
    return protect_keyboard(keyboard, telegram_id)


# ============================================================
# CHARACTER
# ============================================================

async def get_character(
    telegram_id: int,
) -> Character | None:
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == telegram_id)
        )
        if character is not None:
            sync_unlocked_titles(character)
            await session.commit()
            await session.refresh(character)
        return character


# ============================================================
# STATS
# ============================================================

async def get_profile_stats(
    telegram_id: int,
    character: Character,
) -> dict[str, int]:
    try:
        stats = await calculate_character_combat_stats(character)
    except Exception:
        # A schema/query problem in the equipment or pet subsystem must not
        # make the player's profile unavailable. Log the full traceback and
        # render reliable level-based base stats as a safe fallback.
        logger.exception(
            "Failed to calculate full profile stats for telegram_id=%s; "
            "falling back to base stats",
            telegram_id,
        )
        stats = calculate_character_base_stats(character)

    # Display effective combat stats while temporary scroll buffs are active.
    # Combat services apply the same multipliers to damage received/dealt.
    attack = int(stats.attack)
    magic_power = int(stats.magic_power)
    defense = int(stats.defense)
    magic_defense = int(stats.magic_defense)
    try:
        from services.scroll_service import has_buff
        if await has_buff(telegram_id, "power"):
            attack = int(attack * 1.20)
            magic_power = int(magic_power * 1.20)
        if await has_buff(telegram_id, "defense"):
            # Equivalent defense value for a 20% reduction to incoming damage.
            defense = int((defense + 100) / 0.80 - 100)
            magic_defense = int((magic_defense + 100) / 0.80 - 100)
    except Exception:
        logger.exception("Could not apply active scrolls to displayed profile stats")

    return {
        "attack": attack,
        "magic_power": magic_power,
        "defense": defense,
        "magic_defense": magic_defense,
        "hp": int(stats.max_hp),
        "mana": int(stats.max_mana),
        "speed": int(stats.speed),
        "accuracy": int(stats.accuracy),
        "luck": int(stats.luck),
        "critical": int(stats.critical),
    }


# ============================================================
# PROFILE TEXT
# ============================================================

def build_profile_text(
    character: Character,
    active_fan_art: FanArt | None,
    stats: dict[str, int],
) -> str:
    """نمایش پروفایل فارسی با قالب مینیمال و نوارهای متنی."""
    final_hp = max(1, int(stats.get("hp", 1)))
    final_mana = max(1, int(stats.get("mana", 1)))
    current_hp = max(0, min(int(character.hp or 0), final_hp))
    current_mana = max(0, min(int(character.mana or 0), final_mana))

    def bar(current: int, maximum: int, width: int = 10) -> str:
        ratio = max(0.0, min(1.0, current / max(1, maximum)))
        count = min(width, int(ratio * width))
        return "▰" * count + "▱" * (width - count)

    level = max(1, int(character.level or 1))
    xp_progress = build_xp_progress_bar(level=level, xp=int(character.xp or 0))
    combat_power = (
        int(stats.get("attack", 0))
        + int(stats.get("magic_power", 0))
        + int(stats.get("defense", 0)) // 2
        + int(stats.get("magic_defense", 0)) // 2
        + int(stats.get("critical", 0)) * 100
    )
    name = html.escape(str(character.name or "قهرمان بی‌نام"))
    race = html.escape(str(character.race or "نامشخص"))
    title = html.escape(str(character.active_title or title_for_level(level)))

    lines = [
        "✦ 𓂃 <b>قهرمان اِلدوریا</b> 𓂃 ✦",
        "",
        f"👤 {name}",
        f"♛ لقب: {title}",
        f"✧ سطح: {level}",
        f"✧ نژاد: {race}",
        "",
        "━━━━━━━━━━━━━━",
        "",
        f"⚔️ <b>قدرت مبارزه</b>",
        f"└ {combat_power:,}",
        "",
        "❤️ <b>سلامت</b>",
        f"└ {current_hp:,} / {final_hp:,}",
        f"{bar(current_hp, final_hp)} {int(current_hp * 100 / final_hp)}٪",
        "",
        "✧ <b>مانا</b>",
        f"└ {current_mana:,} / {final_mana:,}",
        f"{bar(current_mana, final_mana)} {int(current_mana * 100 / final_mana)}٪",
        "",
        "━━━━━━━━━━━━━━",
        "",
        "✧ <b>تجربه قهرمان</b>",
        xp_progress,
        "",
        "━━━━━━━━━━━━━━",
        "",
        f"🪙 طلا: {int(character.gold or 0):,}",
        f"💎 جم: {int(character.gems or 0):,}",
        "",
    ]
    return "\n".join(lines)


# ============================================================
# SAFE PANEL OUTPUT
# ============================================================

async def replace_with_text_panel(
    callback: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    """
    جایگزینی پنل با کیبورد محافظت‌شده.
    پیام مشترک گروه همچنان یک پیام تلگرام است؛
    کنترل مالکیت دکمه‌ها در middleware انجام می‌شود.
    """

    telegram_id = callback.from_user.id
    markup = owned_keyboard(keyboard, telegram_id)
    message = callback.message

    if message is None:
        return

    try:
        if message.photo:
            await message.delete()
            await message.answer(
                text,
                reply_markup=markup,
                parse_mode=ParseMode.HTML,
            )
        else:
            await message.edit_text(
                text,
                reply_markup=markup,
                parse_mode=ParseMode.HTML,
            )

    except Exception:
        # اگر پیام قابل ویرایش نبود، پیام تازه می‌فرستیم.
        # از حذف اجباری پیام قبلی در این مسیر خودداری می‌کنیم.
        await message.answer(
            text,
            reply_markup=markup,
            parse_mode=ParseMode.HTML,
        )


# ============================================================
# SHOW PROFILE
# ============================================================

async def append_profile_social_and_scrolls(text: str, telegram_id: int) -> str:
    """Use identical social and active-scroll details for all profile entry points."""
    async with AsyncSessionLocal() as session:
        guild_row = (await session.execute(
            select(Guild.name, Guild.tag)
            .join(GuildMember, GuildMember.guild_id == Guild.id)
            .where(GuildMember.telegram_id == telegram_id)
            .limit(1)
        )).first()
        party_row = (await session.execute(
            select(Party.name, Party.rank)
            .join(PartyMember, PartyMember.party_id == Party.id)
            .where(PartyMember.telegram_id == telegram_id, Party.status == "open")
            .limit(1)
        )).first()

    guild_line = (
        f"🛡️ گیلد: <b>{html.escape(guild_row.name)}</b> [{html.escape(guild_row.tag)}]"
        if guild_row else f"🛡️ گیلد: بدون گیلد"
    )
    party_line = (
        f"👥 پارتی: <b>{html.escape(party_row.name)}</b> · رتبه {html.escape(party_row.rank or 'F')}"
        if party_row else f"👥 پارتی: بدون پارتی"
    )
    buffs = await active_buffs(telegram_id)
    if buffs:
        now_ts = datetime.utcnow().timestamp()
        buff_lines = []
        for kind, payload in buffs:
            remaining = max(0, int(float(payload.get("expires_at", 0)) - now_ts))
            hours, minutes = divmod(remaining // 60, 60)
            buff_lines.append(f"• {SCROLLS[kind]['title']} · باقی‌مانده {hours}س {minutes}د")
        scroll_block = f"📜 <b>اسکرول‌های فعال</b>\n" + "\n".join(buff_lines)
    else:
        scroll_block = f"📜 <b>اسکرول‌های فعال</b>\n• هیچ اسکرولی فعال نیست."
    return text + "\n\n━━━━━━━━ 🛡️ پیوندهای قهرمان ⚔️ ━━━━━━━━\n" + guild_line + "\n" + party_line + "\n\n" + scroll_block


async def show_profile(
    callback: CallbackQuery,
) -> None:
    telegram_id = callback.from_user.id

    character = await get_character(telegram_id)

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    stats = await get_profile_stats(
        telegram_id,
        character,
    )

    active_fan_art = await get_active_fan_art(
        telegram_id,
    )

    language = await get_language(telegram_id)
    text = build_profile_text(
        character,
        active_fan_art,
        stats,
    )
    profile_translations = {
        "en": {"قهرمان اِلدوریا":"Eldoria Hero","نام قهرمان":"Hero name","قدرت رزمی":"Combat power","نژاد":"Race","جنسیت":"Gender","هویت قهرمان":"Hero identity","طلا":"Gold","جم":"Gems","وضعیت حیاتی":"Vitals","سلامت":"Health","مانا":"Mana","ویژگی‌های رزمی":"Combat stats","حمله":"Attack","قدرت جادو":"Magic power","دفاع جادویی":"Magic defense","دفاع":"Defense","سرعت":"Speed","دقت":"Accuracy","شانس":"Luck","ضربه بحرانی":"Critical hit","مسیر قهرمانی":"Hero journey","گیلد":"Guild","بدون گیلد":"No guild","پارتی":"Party","بدون پارتی":"No party","پیوندهای قهرمان":"Hero connections","اسکرول‌های فعال":"Active scrolls","هیچ اسکرولی فعال نیست.":"No active scrolls.","باقی‌مانده":"Remaining"},
        "ru": {"قهرمان اِلدوریا":"Герой Элдории","نام قهرمان":"Имя героя","قدرت رزمی":"Боевая сила","نژاد":"Раса","جنسیت":"Пол","هویت قهرمان":"Данные героя","طلا":"Золото","جم":"Самоцветы","وضعیت حیاتی":"Состояние","سلامت":"Здоровье","مانا":"Мана","ویژگی‌های رزمی":"Боевые характеристики","حمله":"Атака","قدرت جادو":"Сила магии","دفاع جادویی":"Магическая защита","دفاع":"Защита","سرعت":"Скорость","دقت":"Точность","شانس":"Удача","ضربه بحرانی":"Критический удар","مسیر قهرمانی":"Путь героя","گیلد":"Гильдия","بدون گیلد":"Нет гильдии","پارتی":"Отряд","بدون پارتی":"Нет отряда","پیوندهای قهرمان":"Связи героя","اسکرول‌های فعال":"Активные свитки","هیچ اسکرولی فعال نیست.":"Нет активных свитков.","باقی‌مانده":"Осталось"}
    }
    for source, target in profile_translations.get(language, {}).items():
        text = text.replace(source, target)

    text = await append_profile_social_and_scrolls(text, telegram_id)

    keyboard = owned_keyboard(
        profile_keyboard(language),
        telegram_id,
    )

    message = callback.message

    if message is None:
        return

    if (
        active_fan_art is not None
        and active_fan_art.image_file_id
    ):
        await message.answer_photo(
            photo=active_fan_art.image_file_id,
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
        return

    # اگر فن‌آرت فعال نیست، از عکس اکانت تلگرام بازیکن استفاده کن.
    try:
        photos = await callback.bot.get_user_profile_photos(telegram_id, limit=1)
        if photos.total_count and photos.photos and message is not None:
            await message.answer_photo(
                photo=photos.photos[0][-1].file_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
            return
    except Exception:
        # نبودن عکس یا خطای API نباید مانع نمایش پروفایل شود.
        pass

    await replace_with_text_panel(
        callback,
        text,
        profile_keyboard(language),
    )


# ============================================================
# COMPACT PROFILE COMMAND (self / replied-to player)
# ============================================================

@router.message(F.text.regexp(r"^(?:/profile(?:@\w+)?|پروفایل)$"))
async def compact_profile_command(message: Message) -> None:
    """نمایش پروفایل جمع‌وجور همراه با تصویر Fan Art بازیکن."""
    if message.from_user is None or not message.text:
        return

    replied_user = (
        message.reply_to_message.from_user
        if message.reply_to_message is not None
        else None
    )
    target_user = replied_user or message.from_user
    if target_user.is_bot:
        await message.answer("❌ نمی‌توان پروفایل این حساب را نمایش داد.")
        return
    target_id = target_user.id

    character = await get_character(target_id)
    if character is None:
        await message.answer(
            "این بازیکن هنوز قهرمانی در اِلدوریا نساخته است."
            if replied_user
            else "ابتدا قهرمانت را از طریق /start بساز."
        )
        return

    try:
        stats = await get_profile_stats(target_id, character)
        max_hp = max(1, int(stats.get("hp", 1) or 1))
        max_mana = max(1, int(stats.get("mana", 1) or 1))
        hp = max(0, min(int(character.hp or 0), max_hp))
        mana = max(0, min(int(character.mana or 0), max_mana))
        level = max(1, int(character.level or 1))
        name = html.escape(str(character.name or "قهرمان بی‌نام"))
        title = html.escape(str(character.active_title or title_for_level(level)))

        async with AsyncSessionLocal() as session:
            guild_row = (await session.execute(
                select(Guild.name, Guild.tag)
                .join(GuildMember, GuildMember.guild_id == Guild.id)
                .where(GuildMember.telegram_id == target_id)
                .limit(1)
            )).first()
            party_row = (await session.execute(
                select(Party.name, Party.rank)
                .join(PartyMember, PartyMember.party_id == Party.id)
                .where(
                    PartyMember.telegram_id == target_id,
                    Party.status == "open",
                )
                .limit(1)
            )).first()

        guild = (
            f"{html.escape(guild_row.name)} [{html.escape(guild_row.tag or '')}]"
            if guild_row else "بدون گیلد"
        )
        party = (
            f"{html.escape(party_row.name)} · رتبه {html.escape(party_row.rank or 'F')}"
            if party_row else "بدون پارتی"
        )

        text = (
            "✦ <b>پروفایل قهرمان</b> ✦\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 نام  ·  <b>{name}</b>\n"
            f"♛ لقب  ·  <b>{title}</b>\n"
            f"✧ سطح  ·  <b>{level:,}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🪙 طلا  ·  <b>{int(character.gold or 0):,}</b>\n"
            f"💎 جم  ·  <b>{int(character.gems or 0):,}</b>\n"
            f"❤️ سلامتی  ·  <b>{hp:,} / {max_hp:,}</b>\n"
            f"💧 مانا  ·  <b>{mana:,} / {max_mana:,}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ گیلد  ·  <b>{guild}</b>\n"
            f"👥 پارتی  ·  <b>{party}</b>"
        )

        active_fan_art = await get_active_fan_art(target_id)
        photo = (
            active_fan_art.image_file_id
            if active_fan_art and active_fan_art.image_file_id
            else None
        )
        if photo is None:
            try:
                photos = await message.bot.get_user_profile_photos(target_id, limit=1)
                if photos.total_count and photos.photos:
                    photo = photos.photos[0][-1].file_id
            except Exception:
                photo = None

        if photo:
            if len(text) <= 1024:
                await message.answer_photo(
                    photo=photo, caption=text, parse_mode=ParseMode.HTML
                )
            else:
                await message.answer_photo(photo=photo)
                await message.answer(text, parse_mode=ParseMode.HTML)
        else:
            await message.answer(text, parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("Failed to render compact profile for telegram_id=%s", target_id)
        await message.answer(
            "❌ نمایش پروفایل با خطای داخلی روبه‌رو شد. جزئیات در ترمینال ربات ثبت شد."
        )


# ============================================================
# OPEN PROFILE
# ============================================================

@router.callback_query(F.data == "menu:profile")
async def profile_handler(
    callback: CallbackQuery,
):
    # پاسخ فوری، تا تلگرام هنگام بارگذاری اطلاعات پروفایل دکمه را معلق نشان ندهد.
    try:
        await callback.answer()
    except Exception:
        pass

    try:
        await show_profile(callback)
    except Exception:
        logger.exception(
            "Failed to open profile for telegram_id=%s",
            callback.from_user.id,
        )
        # خطای پروفایل نباید به شکل کلیک بی‌پاسخ برای بازیکن دیده شود.
        if callback.message is not None:
            try:
                await callback.message.answer(
                    "❌ باز کردن پروفایل با خطا روبه‌رو شد. لطفاً دوباره تلاش کن؛ جزئیات خطا در لاگ ربات ثبت شد."
                )
            except Exception:
                pass


# ============================================================
# FULL STATS
# ============================================================

@router.callback_query(F.data == "profile:titles")
async def profile_titles_handler(callback: CallbackQuery):
    await render_titles(callback, 0)
    await callback.answer()


@router.callback_query(F.data.startswith("profile:titlepage:"))
async def profile_titles_page_handler(callback: CallbackQuery):
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        page = 0
    await render_titles(callback, page)
    await callback.answer()


@router.callback_query(F.data.startswith("profile:settitle:"))
async def profile_set_title_handler(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    try:
        title_level = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ لقب نامعتبر است.", show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == telegram_id))
        if character is None:
            await callback.answer("❌ قهرمان پیدا نشد.", show_alert=True)
            return
        unlocked = sync_unlocked_titles(character)
        if title_level not in unlocked or title_level > int(character.level or 1):
            await callback.answer("🔒 این لقب هنوز باز نشده است.", show_alert=True)
            return
        character.active_title = TITLES[title_level - 1]
        await session.commit()
    await render_titles(callback, (title_level - 1) // 10)
    await callback.answer("✅ لقب قهرمان تغییر کرد.")


@router.callback_query(F.data == "profile:stats")
async def profile_stats_handler(
    callback: CallbackQuery,
):
    telegram_id = callback.from_user.id

    character = await get_character(telegram_id)

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    stats = await get_profile_stats(
        telegram_id,
        character,
    )

    final_hp = int(stats.get("hp", 0))
    final_mana = int(stats.get("mana", 0))

    current_hp = min(
        int(character.hp or 0),
        final_hp,
    )
    current_mana = min(
        int(character.mana or 0),
        final_mana,
    )

    xp_progress = build_xp_progress_bar(
        level=character.level,
        xp=character.xp,
    )

    text = (
        "📊 <b>آمار کامل قهرمان</b>\n\n"
        f"👤 {character.name}\n"
        f"⭐ سطح: {character.level}\n\n"
        "🎖️ <b>پیشرفت لول‌آپ</b>\n"
        f"{xp_progress}\n\n"
        f"❤️ HP: {current_hp}/{final_hp}\n"
        f"💧 Mana: {current_mana}/{final_mana}\n\n"
        f"⚔️ حمله: {stats['attack']}\n"
        f"🔮 قدرت جادو: {stats['magic_power']}\n"
        f"🛡️ دفاع: {stats['defense']}\n"
        f"✨ دفاع جادویی: {stats['magic_defense']}\n"
        f"💨 سرعت: {stats['speed']}\n"
        f"🎯 دقت: {stats['accuracy']}\n"
        f"🍀 شانس: {character.luck}\n"
        f"💥 کریتیک: {stats['critical']}\n\n"
        f"💰 طلا: {character.gold:,}\n"
        f"💎 جم: {character.gems:,}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به پروفایل",
                    callback_data="menu:profile",
                )
            ]
        ]
    )

    await replace_with_text_panel(
        callback,
        text,
        keyboard,
    )
    await callback.answer()


# ============================================================
# FAN ART LIST
# ============================================================

@router.callback_query(F.data == "profile:fanart")
async def profile_fan_art_handler(
    callback: CallbackQuery,
):
    telegram_id = callback.from_user.id

    character = await get_character(telegram_id)

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    fan_arts = await get_owned_fan_arts(
        telegram_id,
    )

    if not fan_arts:
        text = (
            "🎨 <b>Fan Art پروفایل</b>\n\n"
            "📭 هنوز هیچ Fan Artای در اختیار نداری.\n\n"
            "ابتدا یک Fan Art تهیه کن تا بتوانی آن را "
            "به عنوان تصویر پروفایل انتخاب کنی."
        )

        await replace_with_text_panel(
            callback,
            text,
            profile_fan_art_keyboard(
                [],
                character.active_fan_art_id,
            ),
        )

        await callback.answer()
        return

    text = (
        "🎨 <b>Fan Art پروفایل</b>\n\n"
        "Fan Art موردنظر خودت را برای نمایش در پروفایل انتخاب کن.\n\n"
    )

    active_name = next(
        (
            fan_art.name
            for fan_art in fan_arts
            if fan_art.id == character.active_fan_art_id
        ),
        None,
    )

    if active_name:
        text += f"✅ فعال: {active_name}\n\n"

    text += "یکی از Fan Artهای مالکیت‌شده را انتخاب کن:"

    await replace_with_text_panel(
        callback,
        text,
        profile_fan_art_keyboard(
            fan_arts,
            character.active_fan_art_id,
        ),
    )

    await callback.answer()


# ============================================================
# SET ACTIVE FAN ART
# ============================================================

@router.callback_query(
    F.data.startswith("profile:setfanart:")
)
async def set_profile_fan_art_handler(
    callback: CallbackQuery,
):
    try:
        fan_art_id = int(
            callback.data.split(":")[2]
        )
    except (ValueError, IndexError, AttributeError):
        await callback.answer(
            "❌ Fan Art نامعتبر است.",
            show_alert=True,
        )
        return

    telegram_id = callback.from_user.id

    success, result_message = await set_active_fan_art(
        telegram_id,
        fan_art_id,
    )

    if not success:
        await callback.answer(
            result_message,
            show_alert=True,
        )
        return

    await show_profile(callback)
    await callback.answer("🎨 Fan Art فعال شد.")


# ============================================================
# CLEAR ACTIVE FAN ART
# ============================================================

@router.callback_query(
    F.data == "profile:clearfanart"
)
async def clear_profile_fan_art_handler(
    callback: CallbackQuery,
):
    telegram_id = callback.from_user.id

    success, result_message = await clear_active_fan_art(
        telegram_id,
    )

    if not success:
        await callback.answer(
            result_message,
            show_alert=True,
        )
        return

    await show_profile(callback)
    await callback.answer("🚫 Fan Art فعال حذف شد.")

