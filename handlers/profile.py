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
from services.panel_image_service import replace_panel_with_photo, replace_panel_with_text
from services.image_aspect_service import prepare_photo

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
from services.premium_emoji_service import emoji, load


router = Router()
logger = logging.getLogger(__name__)


# ============================================================
# XP PROGRESS BAR
# ============================================================

def build_xp_progress_bar(
    level: int,
    xp: int,
) -> str:
    """
    ساخت نوار پیشرفت XP تا سطح بعدی با استفاده از
    فرمول اصلی services/xp_service.py.
    """

    level = max(1, int(level or 1))
    xp = max(0, int(xp or 0))

    # قهرمان به حداکثر سطح رسیده است.
    if level >= MAX_CHARACTER_LEVEL:
        bar = emoji("profile_xp_fill") * 10

        return (
            f"{bar}\n"
            "📈 پیشرفت سطح: ۱۰۰٪ (حداکثر سطح)\n"
            "🏆 به حداکثر سطح رسیده‌ای!"
        )

    required_xp = get_required_xp(level)

    # محافظت در برابر مقدار نامعتبر یا صفر
    if required_xp <= 0:
        bar = "🟩" * 10

        return (
            f"{bar}\n"
            "📈 پیشرفت تا سطح بعدی: ۱۰۰٪\n"
            "✨ XP موردنیاز: ۰"
        )

    current_xp = min(xp, required_xp)
    percentage = min(
        100,
        int(current_xp * 100 / required_xp),
    )

    filled_blocks = min(
        10,
        int(current_xp * 10 / required_xp),
    )

    empty_blocks = 10 - filled_blocks

    bar = (
        emoji("profile_xp_fill") * filled_blocks
        + emoji("profile_xp_empty") * empty_blocks
    )

    return (
        f"{bar}\n"
        f"📈 پیشرفت تا سطح بعدی: {percentage}٪\n"
        f"✨ XP: {xp:,} / {required_xp:,}"
    )


# ============================================================
# KEYBOARDS
# ============================================================

def profile_keyboard() -> InlineKeyboardMarkup:
    # This is the keyboard actually used by handlers/profile.py for both the
    # /profile flow and returning to the profile from the main menu (/menu).
    # Read the IDs configured in the emoji admin archive here, at render time.
    data = load()
    ids = data.get("ids", {})
    enabled = bool(data.get("enabled"))

    def button(key: str, fallback: str, label: str, callback_data: str) -> InlineKeyboardButton:
        emoji_id = str(ids.get(key, "") or "")
        if enabled and emoji_id.isdigit():
            return InlineKeyboardButton(
                text=label,
                callback_data=callback_data,
                icon_custom_emoji_id=emoji_id,
            )
        return InlineKeyboardButton(
            text=f"{fallback} {label}",
            callback_data=callback_data,
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button("profile_inventory", "🗃️", "صندوقچه", "menu:inventory"),
                button("profile_equipment", "🗡️", "تجهیزات", "menu:equipment"),
            ],
            [
                button("profile_skills", "⚔️", "مهارت‌ها", "menu:skills"),
                button("profile_stats", "📊", "آمار کامل", "profile:stats"),
            ],
            [
                button(
                    "profile_fanart_select",
                    "🖼️",
                    "انتخاب Fan Art پروفایل",
                    "profile:fanart",
                ),
            ],
            [
                button("profile_back", "🔙", "بازگشت", "menu:back"),
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
    await replace_with_text_panel(
        callback,
        text,
        title_keyboard(unlocked, active_title, page),
    )


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
    """Render a compact, ornate fantasy profile that fits Telegram captions."""
    final_hp = max(1, int(stats.get("hp", 1)))
    final_mana = max(1, int(stats.get("mana", 1)))
    current_hp = max(0, min(int(character.hp or 0), final_hp))
    current_mana = max(0, min(int(character.mana or 0), final_mana))

    def bar(current: int, maximum: int, filled: str, empty: str = "▫️", width: int = 8) -> str:
        ratio = max(0.0, min(1.0, current / max(1, maximum)))
        count = min(width, int(ratio * width))
        return filled * count + empty * (width - count)

    level = max(1, int(character.level or 1))
    xp_progress = build_xp_progress_bar(level=level, xp=int(character.xp or 0))
    # A readable, comparable combat rating; it is informational and doesn't alter combat math.
    combat_power = (
        int(stats.get("attack", 0))
        + int(stats.get("magic_power", 0))
        + int(stats.get("defense", 0)) // 2
        + int(stats.get("magic_defense", 0)) // 2
        + int(stats.get("critical", 0)) * 100
    )
    name = html.escape(str(character.name or "قهرمان بی‌نام"))
    race = html.escape(str(character.race or "نامشخص"))
    gender_value = getattr(character, "gender", None)
    gender = "مرد" if gender_value == "male" else "زن" if gender_value == "female" else "ثبت نشده"
    title = html.escape(str(character.active_title or title_for_level(level)))

    lines = [
        "╗═══════ ✦ اِلدوریا ✦ ═══════╔",
        "  ⚔️ <b>قهرمان اِلدوریا</b> ⚔️",
        "",
        f"🧙 نام قهرمان: <b>{name}</b>",
        f"🎖️ لقب: {title}",
        f"🏅 سطح: Lv. {level}",
        f"🧬 نژاد: {race}  ·  ⚧️ جنسیت: {gender}",
        "",
        "━━━━━━━━ ⚜️ هویت قهرمان ⚜️ ━━━━━━━━",
        "",
        f"⚔️ قدرت رزمی: <b>{combat_power:,}</b>",
        f"💰 طلا: <b>{int(character.gold or 0):,}</b>  ·  💎 جم: <b>{int(character.gems or 0):,}</b>",
        "",
        "━━━━━━━━ ❤️ وضعیت حیاتی 💧 ━━━━━━━━",
        "",
        f"❤️ سلامت (HP): <b>{current_hp:,} / {final_hp:,}</b>",
        f"{bar(current_hp, final_hp, '🟥', empty='⬜️')}",
        "",
        f"💧 مانا (Mana): <b>{current_mana:,} / {final_mana:,}</b>",
        f"{bar(current_mana, final_mana, '🟦', empty='⬜️')}",
        "",
        "━━━━━━━━ ⚔️ ویژگی‌های رزمی ⚔️ ━━━━━━━━",
        "",
        f"⚔️ حمله: <b>{int(stats.get('attack', 0)):,}</b>  ·  🔮 قدرت جادو: <b>{int(stats.get('magic_power', 0)):,}</b>",
        f"🛡️ دفاع: <b>{int(stats.get('defense', 0)):,}</b>  ·  ✨ دفاع جادویی: <b>{int(stats.get('magic_defense', 0)):,}</b>",
        f"💨 سرعت: <b>{int(stats.get('speed', 0)):,}</b>  ·  🎯 دقت: <b>{int(stats.get('accuracy', 0)):,}</b>",
        f"🍀 شانس: <b>{int(getattr(character, 'luck', 0) or stats.get('luck', 0)):,}</b>  ·  💥 ضربه بحرانی: <b>{int(stats.get('critical', 0))}%</b>",
        "",
        "━━━━━━━━ 🌟 مسیر قهرمانی 🌟 ━━━━━━━━",
        "",
        xp_progress,
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
    """Replace the current player panel in-place, re-sending only when media changes."""
    await replace_panel_with_text(
        callback=callback,
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )

# ============================================================
# SHOW PROFILE
# ============================================================

async def append_profile_social_and_scrolls(text: str, telegram_id: int) -> str:
    """Append social links and active buffs in one compact caption line each."""
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
        f"🏰 {html.escape(guild_row.name)} [{html.escape(guild_row.tag)}]"
        if guild_row else "🏰 بدون گیلد"
    )
    party_line = (
        f"👥 {html.escape(party_row.name)} · رتبه {html.escape(party_row.rank or 'F')}"
        if party_row else "👥 بدون پارتی"
    )
    buffs = await active_buffs(telegram_id)
    if buffs:
        now_ts = datetime.utcnow().timestamp()
        buff_lines = []
        for kind, payload in buffs:
            remaining = max(0, int(float(payload.get("expires_at", 0)) - now_ts))
            hours, minutes = divmod(remaining // 60, 60)
            buff_lines.append(f"{SCROLLS[kind]['title']} ({hours}س {minutes}د)")
        scroll_line = "✨ " + "، ".join(buff_lines[:3])
        if len(buff_lines) > 3:
            scroll_line += f" +{len(buff_lines) - 3}"
    else:
        scroll_line = "✨ اسکرول فعال ندارد"
    return text + "\n" + guild_line + " · " + party_line + "\n" + scroll_line



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

    text = build_profile_text(
        character,
        active_fan_art,
        stats,
    )

    text = await append_profile_social_and_scrolls(text, telegram_id)

    keyboard = owned_keyboard(
        profile_keyboard(),
        telegram_id,
    )

    # Full profile may exceed Telegram's photo caption limit.
    if len(text) > 1024:
        await replace_with_text_panel(callback, text, keyboard)
        return

    message = callback.message

    if message is None:
        return

    # پروفایل یکی از استثناهای تصویری است؛ پنل قبلی حذف و تصویر جدید جایگزین می‌شود.
    if active_fan_art is not None and active_fan_art.image_file_id:
        await replace_panel_with_photo(
            callback=callback,
            photo=active_fan_art.image_file_id,
            caption=text,
            reply_markup=profile_keyboard(),
            parse_mode=ParseMode.HTML,
            portrait=True,
        )
        return

    # اگر فن‌آرت فعال نیست، از عکس اکانت تلگرام بازیکن استفاده کن.
    try:
        photos = await callback.bot.get_user_profile_photos(telegram_id, limit=1)
        if photos.total_count and photos.photos:
            await replace_panel_with_photo(
                callback=callback,
                photo=photos.photos[0][-1].file_id,
                caption=text,
                reply_markup=profile_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            return
    except Exception:
        # نبودن عکس یا خطای API نباید مانع نمایش پروفایل شود.
        pass

    await replace_with_text_panel(callback, text, profile_keyboard())


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

@router.message(F.text.func(lambda text: bool(text) and text.strip().casefold() == "\u067e\u0631\u0648\u0641\u0627\u06cc\u0644"))
@router.message(Command("profile", ignore_case=True))
async def profile_command(message: Message):
    """نمایش پروفایل خود یا صاحب پیامی که دستور به آن ریپلای شده است."""
    if not message.from_user:
        return
    target_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if target_user is None or target_user.is_bot:
        await message.answer("❌ نمی‌توان پروفایل این حساب را نمایش داد.")
        return

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == target_user.id)
        )
    if character is None:
        await message.answer("این بازیکن هنوز حساب World Eldoria نساخته است.")
        return

    try:
        stats = await get_profile_stats(target_user.id, character)
        active_fan_art = await get_active_fan_art(target_user.id)
        text = build_profile_text(character, active_fan_art, stats)
        text = await append_profile_social_and_scrolls(text, target_user.id)
    except Exception:
        logger.exception(
            "Failed to render /profile for telegram_id=%s",
            target_user.id,
        )
        await message.answer(
            "❌ پروفایل به‌دلیل خطای داخلی کامل باز نشد. جزئیات خطا در ترمینال ربات ثبت شد."
        )
        return

    # فن‌آرت انتخاب‌شده همیشه اولویت دارد؛ در نبود آن عکس پروفایل تلگرام استفاده می‌شود.
    photo = active_fan_art.image_file_id if active_fan_art and active_fan_art.image_file_id else None
    if photo is None:
        try:
            photos = await message.bot.get_user_profile_photos(target_user.id, limit=1)
            if photos.total_count and photos.photos:
                photo = photos.photos[0][-1].file_id
        except Exception:
            photo = None

    # Telegram photo captions are limited to 1024 characters. Never drop
    # guild, party or active-scroll details to make a profile fit a caption.
    if photo:
        if len(text) <= 1024:
            try:
                prepared_photo = await prepare_photo(
                    message.bot,
                    photo,
                    filename="eldoria-profile.jpg",
                    portrait=True,
                )
            except Exception:
                logger.exception("Could not normalize profile photo; sending original as fallback")
                prepared_photo = photo
            await message.answer_photo(
                photo=prepared_photo,
                caption=text,
                parse_mode=ParseMode.HTML,
            )
        else:
            try:
                prepared_photo = await prepare_photo(
                    message.bot,
                    photo,
                    filename="eldoria-profile.jpg",
                    portrait=True,
                )
            except Exception:
                logger.exception("Could not normalize profile photo; sending original as fallback")
                prepared_photo = photo
            await message.answer_photo(photo=prepared_photo)
            await message.answer(text, parse_mode=ParseMode.HTML)
    else:
        await message.answer(text, parse_mode=ParseMode.HTML)
