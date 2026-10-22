from __future__ import annotations

import html
import json
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from aiogram.fsm.context import FSMContext
from states.social import HeroRename
from middlewares.panel_owner import protect_keyboard
from models.item import Item
from models.inventory import Inventory
from models.equipment import Equipment

from database.database import AsyncSessionLocal
from models.character import Character
from models.fan_art import FanArt, FanArtOwnership
from models.social_systems import PlayerSetting
from services.social_service import *
from services.panel_image_service import show_panel
from services.language_service import get_language, tr

router = Router()
logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

async def menu(
    callback: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
    *,
    answer_callback: bool = True,
):
    """Send a new text panel and preserve all earlier chat messages."""
    message = callback.message
    if keyboard is not None and callback.from_user is not None:
        is_shared_dungeon = bool(message and message.chat.type in {"group", "supergroup"}) and any(
            (button.callback_data or "").startswith("dungeon:")
            for row in keyboard.inline_keyboard for button in row
        )
        if not is_shared_dungeon:
            keyboard = protect_keyboard(keyboard, callback.from_user.id)

    if message is not None:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    if answer_callback:
        try:
            await callback.answer()
        except Exception:
            pass


async def settings_panel(
    callback: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
):
    await show_panel(
        callback=callback,
        panel_name="settings",
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    try:
        await callback.answer()
    except Exception:
        pass


async def pvp_panel(
    callback: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
):
    await show_panel(
        callback=callback,
        panel_name="pvp",
        text=text,
        reply_markup=keyboard,
        parse_mode=None,
    )

    try:
        await callback.answer()
    except Exception:
        pass


async def character(telegram_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )
        return result.scalar_one_or_none()


async def get_profile_fan_art(
    telegram_id: int,
) -> FanArt | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FanArt)
            .join(
                FanArtOwnership,
                FanArtOwnership.fan_art_id == FanArt.id,
            )
            .join(
                Character,
                Character.active_fan_art_id == FanArt.id,
            )
            .where(
                Character.telegram_id == telegram_id,
                FanArtOwnership.telegram_id == telegram_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()


# ============================================================
# Settings
# ============================================================

@router.callback_query(F.data == "menu:settings")
async def settings_menu(callback: CallbackQuery):
    language = await get_language(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(language, "rename"), callback_data="settings:rename")],
        [InlineKeyboardButton(text=tr(language, "language"), callback_data="settings:language")],
        [InlineKeyboardButton(text=tr(language, "back"), callback_data="menu:back")],
    ])
    await settings_panel(callback, tr(language, "settings"), keyboard)


@router.callback_query(F.data == "settings:notifications")
async def settings_notifications(callback: CallbackQuery):
    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PlayerSetting).where(
                PlayerSetting.telegram_id == telegram_id
            )
        )
        setting = result.scalar_one_or_none()

        if setting is None:
            setting = PlayerSetting(
                telegram_id=telegram_id,
                notifications=True,
            )
            session.add(setting)
            await session.commit()

        notifications_enabled = bool(setting.notifications)

    status = "فعال است" if notifications_enabled else "غیرفعال است"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=("🔕 خاموش‌کردن اعلان‌ها" if notifications_enabled else "🔔 روشن‌کردن اعلان‌ها"), callback_data="settings:notifications:toggle")],
            [InlineKeyboardButton(text="📥 صندوق اعلان‌ها", callback_data="menu:notifications")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:settings")],
        ]
    )

    await settings_panel(
        callback,
        f"🔔 اعلان‌ها\n\nوضعیت اعلان‌ها: {status}",
        keyboard,
    )


@router.callback_query(F.data == "settings:notifications:toggle")
async def settings_notifications_toggle(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        setting = await session.scalar(select(PlayerSetting).where(PlayerSetting.telegram_id == telegram_id).with_for_update())
        if setting is None:
            setting = PlayerSetting(telegram_id=telegram_id, notifications=False)
            session.add(setting)
        else:
            setting.notifications = not bool(setting.notifications)
        enabled = bool(setting.notifications)
        await session.commit()
    await callback.answer("اعلان‌ها فعال شد." if enabled else "اعلان‌ها غیرفعال شد.")
    await settings_notifications(callback)


@router.callback_query(F.data == "settings:language")
async def settings_language(callback: CallbackQuery):
    language = await get_language(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=("✅ " if language == "fa" else "") + "🇮🇷 فارسی", callback_data="settings:language:fa")],
        [InlineKeyboardButton(text=("✅ " if language == "en" else "") + "🇬🇧 English", callback_data="settings:language:en")],
        [InlineKeyboardButton(text=("✅ " if language == "ru" else "") + "🇷🇺 Русский", callback_data="settings:language:ru")],
        [InlineKeyboardButton(text=tr(language, "back"), callback_data="menu:settings")],
    ])
    await settings_panel(callback, tr(language, "choose"), keyboard)


@router.callback_query(F.data.startswith("settings:language:"))
async def settings_language_set(callback: CallbackQuery):
    language = callback.data.rsplit(":", 1)[-1]
    if language not in {"fa", "en", "ru"}:
        await callback.answer("Invalid language / زبان نامعتبر", show_alert=True)
        return
    telegram_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        setting = await session.scalar(select(PlayerSetting).where(PlayerSetting.telegram_id == telegram_id).with_for_update())
        if setting is None:
            setting = PlayerSetting(telegram_id=telegram_id, language=language)
            session.add(setting)
        else:
            setting.language = language
        await session.commit()
    await callback.answer(tr(language, "saved"))
    await settings_language(callback)


# ============================================================
# Hero rename (2,000 Gold)
# ============================================================

RENAME_HERO_COST = 2000


@router.callback_query(F.data == "settings:rename")
async def settings_rename_start(callback: CallbackQuery, state: FSMContext):
    if callback.message is None or callback.message.chat.type != "private":
        await callback.answer("برای تغییر نام، تنظیمات را در گفت‌وگوی خصوصی ربات باز کن.", show_alert=True)
        return
    player = await character(callback.from_user.id)
    if player is None:
        await callback.answer("ابتدا قهرمان خودت را بساز.", show_alert=True)
        return
    await state.set_state(HeroRename.waiting_for_name)
    await state.update_data(rename_owner_id=callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="لغو", callback_data="settings:rename:cancel")
    ]])
    await settings_panel(
        callback,
        f"✍️ <b>تغییر نام قهرمان</b>\n\nنام فعلی: <b>{html.escape(player.name)}</b>\nهزینه: <b>{RENAME_HERO_COST:,} Gold</b>\n\nنام جدید را در پیام بعدی بفرست. نام باید ۲ تا ۲۴ نویسه باشد.",
        keyboard,
    )


@router.callback_query(F.data == "settings:rename:cancel")
async def settings_rename_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await settings_menu(callback)


@router.message(HeroRename.waiting_for_name)
async def settings_rename_receive(message: Message, state: FSMContext):
    if message.from_user is None or not message.text:
        await message.answer("لطفاً نام جدید را به‌صورت متن ارسال کن.")
        return
    data = await state.get_data()
    if data.get("rename_owner_id") != message.from_user.id:
        await state.clear()
        return
    new_name = " ".join(message.text.strip().split())
    if not 2 <= len(new_name) <= 24:
        await message.answer("نام باید بین ۲ تا ۲۴ نویسه باشد. دوباره تلاش کن.")
        return
    if any(ord(ch) < 32 for ch in new_name) or "<" in new_name or ">" in new_name:
        await message.answer("این نام قابل قبول نیست؛ نام دیگری انتخاب کن.")
        return

    async with AsyncSessionLocal() as session:
        player = await session.scalar(select(Character).where(
            Character.telegram_id == message.from_user.id
        ).with_for_update())
        if player is None:
            await state.clear()
            await message.answer("قهرمان پیدا نشد.")
            return
        if player.name.casefold() == new_name.casefold():
            await state.clear()
            await message.answer("نام جدید با نام فعلی یکسان است؛ Gold کسر نشد.")
            return
        existing = await session.scalar(select(Character.id).where(
            Character.name.ilike(new_name)
        ).limit(1))
        if existing is not None:
            await message.answer("این نام قبلاً انتخاب شده است. نام دیگری بفرست.")
            return
        if player.gold < RENAME_HERO_COST:
            await state.clear()
            await message.answer(f"Gold کافی نداری. هزینهٔ تغییر نام {RENAME_HERO_COST:,} Gold است.")
            return
        old_name = player.name
        player.name = new_name
        player.gold -= RENAME_HERO_COST
        await session.commit()

    await state.clear()
    await message.answer(
        f"✨ نام قهرمان با موفقیت تغییر کرد!\n\n"
        f"نام قبلی: {html.escape(old_name)}\n"
        f"نام جدید: <b>{html.escape(new_name)}</b>\n"
        f"💰 هزینه: {RENAME_HERO_COST:,} Gold",
        parse_mode="HTML",
    )


# ============================================================
# Ranking
# ============================================================

@router.callback_query(F.data == "menu:ranking")
async def ranking_menu(callback: CallbackQuery):
    rankings = await get_ranking()
    lines = ["🏆 <b>تالار افتخارات اِلدوریا</b>", "قهرمانانی که نامشان در سالنامهٔ جهان ثبت شده است:", ""]
    if not rankings:
        lines.append("هنوز قهرمانی برای رتبه‌بندی وجود ندارد.")
    else:
        from services.character_stats_service import calculate_character_combat_stats
        for index, player in enumerate(rankings[:10], start=1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, "🔹")
            name = html.escape(str(getattr(player, "name", "قهرمان")))
            username = getattr(player, "telegram_username", None)
            identity = f"@{username}" if username else f"ID {player.telegram_id}"
            try:
                stats = await calculate_character_combat_stats(player)
                power = stats.attack * 4 + stats.magic_power * 4 + stats.defense * 3 + stats.magic_defense * 3 + stats.max_hp // 2 + stats.max_mana // 3
            except Exception:
                power = 0
            lines.append(f"{medal} <b>{index}. {name}</b> · Lv.{player.level}\n   🪪 <code>{html.escape(identity)}</code> · ⚔️ قدرت رزمی: <b>{power:,}</b>")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 تازه‌سازی", callback_data="menu:ranking")],[InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:back")]])
    await menu(callback, "\n".join(lines), keyboard)


# ============================================================
# PvP
# ============================================================

@router.callback_query(F.data == "menu:pvp")
async def pvp_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📜 راهنمای حمله",
                    callback_data="pvp:help",
                ),
            ],
            [InlineKeyboardButton(text="🏆 لیگ PvP", callback_data="menu:pvp_league")],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="menu:back",
                )
            ],
        ]
    )

    await pvp_panel(
        callback,
        "⚔️ <b>نبردهای مستقیم اِلدوریا</b>\n\n"
        "برای حمله، در گروه روی پیام بازیکن ریپلای کن و بنویس «حمله».\n"
        "هیچ درخواستی ارسال نمی‌شود؛ ضربه بلافاصله محاسبه می‌شود.\n\n"
        "💰 هر ضربه: پاداشی برابر ۱٫۵٪ گلد هدف، بدون کسر از او.\n"
        "☠️ با شکست کامل هدف: ۵٪ گلد او نیز به‌عنوان غارت واقعی منتقل می‌شود.\n"
        "⏳ پس از مرگ، ۱۰ دقیقه محرومیت از نبرد و سپس احیای کامل.",
        keyboard,
    )


@router.callback_query(F.data == "pvp:help")
async def pvp_help(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="menu:pvp",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 منوی اصلی",
                    callback_data="menu:back",
                )
            ],
        ]
    )

    await pvp_panel(
        callback,
        "⚔️ <b>راهنمای حمله</b>\n\n"
        "۱. در گروه روی پیام هدف ریپلای کن.\n"
        "۲. فقط کلمهٔ «حمله» را بفرست.\n\n"
        "حمله فوری است و از هدف اجازه گرفته نمی‌شود. پاداش هر حمله ۱٫۵٪ دارایی گلدی اوست؛ این پاداش از حریف کسر نمی‌شود. اگر او را شکست بدهی، ۵٪ گلدش واقعاً کسر می‌شود و به تو می‌رسد.\n"
        "بازیکن کشته‌شده ۱۰ دقیقه از نبرد محروم است و بعد با HP و مانای کامل زنده می‌شود.",
        keyboard,
    )


# ============================================================
# Crafting
# ============================================================

@router.callback_query(F.data == "menu:crafting")
async def crafting_menu(callback: CallbackQuery):
    recipe_list = await recipes()
    player = await character(callback.from_user.id)
    crafting_xp = int(getattr(player, "crafting_xp", 0) or 0) if player else 0
    rows = []
    for recipe in recipe_list[:20]:
        rows.append([InlineKeyboardButton(
            text=f"🔹 {recipe.name} · Lv.{recipe.required_level}",
            callback_data=f"crafting:recipe:{recipe.id}",
        )])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    text = (
        "🔨 <b>کارگاه کرفتینگ اِلدوریا</b>\n\n"
        f"✨ XP کرفتینگ: <b>{crafting_xp:,}</b>\n\n"
        "دستور ساخت را انتخاب کن. مواد و Gold فقط پس از بررسی کامل و موفقیت ساخت مصرف می‌شوند.\n"
        "ساخت هر آیتم ۵ XP کرفتینگ به ازای هر عدد می‌دهد و پیشرفت آن جدا از XP مهارت‌های رزمی ذخیره می‌شود."
    )
    if not recipe_list:
        text += "\n\nفعلاً دستور ساختی ثبت نشده است. مدیر بازی باید دستورها را با اسکریپت seed اضافه کند."
    await menu(callback, text, keyboard)


@router.callback_query(F.data.startswith("crafting:recipe:"))
async def crafting_recipe_detail(callback: CallbackQuery):
    try:
        recipe_id = int(callback.data.rsplit(":", 1)[-1])
    except (TypeError, ValueError):
        await callback.answer("دستور ساخت نامعتبر است.", show_alert=True)
        return
    recipe = next((r for r in await recipes() if r.id == recipe_id), None)
    if recipe is None:
        await callback.answer("این دستور ساخت در دسترس نیست.", show_alert=True)
        return
    try:
        material_data = json.loads(recipe.materials_json or "{}")
    except (ValueError, TypeError):
        material_data = {}
    material_lines = []
    async with AsyncSessionLocal() as session:
        player = await session.scalar(select(Character).where(Character.telegram_id == callback.from_user.id))
        for raw_id, amount in material_data.items():
            item_id = int(raw_id)
            item = await session.get(Item, item_id)
            inv = await session.scalar(select(Inventory).where(
                Inventory.character_id == player.id if player else False,
                Inventory.item_id == item_id,
            )) if player else None
            have = int(inv.quantity) if inv else 0
            needed = int(amount)
            mark = "✅" if have >= needed else "❌"
            material_lines.append(f"{mark} {html.escape(item.name if item else f'ماده #{raw_id}')} · {have}/{needed}")
        output_item = await session.get(Item, recipe.result_item_id) if recipe.result_item_id else None
        output_equipment = await session.get(Equipment, recipe.result_equipment_id) if recipe.result_equipment_id else None
        output_name = output_item.name if output_item else (output_equipment.name if output_equipment else "خروجی تعریف‌نشده")
        output_description = (output_item.description or "") if output_item and output_item.item_type == "scroll" else ""
    scroll_description = f"📖 <b>اثر اسکرول</b>\n{html.escape(output_description)}\n\n" if output_description else ""
    text = (
        f"🔨 <b>{html.escape(recipe.name)}</b>\n\n"
        f"🎁 خروجی: {html.escape(output_name)} × 1\n"
        f"{scroll_description}"
        f"💰 هزینهٔ ساخت هر عدد: {int(recipe.gold_cost):,} Gold\n"
        f"⭐ سطح موردنیاز: {recipe.required_level}\n\n"
        f"🧱 <b>مواد لازم برای هر عدد</b>\n" + ("\n".join(material_lines) if material_lines else "بدون مواد اولیه") +
        "\n\nتعداد ساخت را انتخاب کن:"
    )
    rows = []
    for qty in (1, 5, 10, 20, 50):
        rows.append([InlineKeyboardButton(text=f"ساخت {qty}×", callback_data=f"crafting:make:{recipe.id}:{qty}")])
    rows.append([InlineKeyboardButton(text="🔙 فهرست دستورها", callback_data="menu:crafting")])
    await menu(callback, text, InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("crafting:make:"))
async def crafting_make(callback: CallbackQuery):
    try:
        _, _, recipe_id, quantity = callback.data.split(":", 3)
        recipe_id, quantity = int(recipe_id), int(quantity)
    except (TypeError, ValueError):
        await callback.answer("درخواست ساخت معتبر نیست.", show_alert=True)
        return
    success, result_text = await craft(callback.from_user.id, recipe_id, quantity)
    if not success:
        await callback.answer(result_text[:180], show_alert=True)
        return
    try:
        from services.world_progression_service import log_progress
        await log_progress(callback.from_user.id, "craft", f"recipe={recipe_id};quantity={quantity}")
    except Exception:
        logger.exception("Could not log crafting progress")
    await callback.answer("ساخت با موفقیت انجام شد!")
    await menu(callback, "✨ <b>نتیجهٔ کرفتینگ</b>\n\n" + html.escape(result_text), InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 ساخت دوباره", callback_data=f"crafting:recipe:{recipe_id}")],
        [InlineKeyboardButton(text="📜 دستورهای دیگر", callback_data="menu:crafting")],
        [InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="menu:back")],
    ]), answer_callback=False)


# ============================================================
# Pets
# ============================================================

@router.callback_query(F.data == "menu:pets")
async def pets_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🐾 حیوانات من",
                    callback_data="pets:list",
                ),
            ],
            [InlineKeyboardButton(text="🛒 بازار پت‌ها", callback_data="pets:market")],
            [InlineKeyboardButton(text="✨ تمرین/تکامل پت فعال", callback_data="pets:evolve")],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="menu:back",
                )
            ],
        ]
    )

    await menu(
        callback,
        "🐾 Pets\n\n"
        "حیوانات همراه خود را مدیریت کن.",
        keyboard,
    )


@router.callback_query(F.data == "pets:list")
async def pets_list(callback: CallbackQuery):
    from handlers.advanced_world import pets_menu_for_user
    await pets_menu_for_user(callback)


# ============================================================
# Events
# ============================================================

@router.callback_query(F.data == "menu:events")
async def events_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎉 رویدادهای فعال",
                    callback_data="events:list",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="menu:back",
                )
            ],
        ]
    )

    await menu(
        callback,
        "🎉 رویدادها\n\n"
        "رویدادهای ویژه اِلدوریا را دنبال کن.",
        keyboard,
    )


@router.callback_query(F.data == "events:list")
async def events_list(callback: CallbackQuery):
    await callback.answer(
        "🎉 فعلاً رویداد فعالی وجود ندارد.",
        show_alert=True,
    )


# ============================================================
# /pvp
# ============================================================

@router.message(F.text.regexp(r"^/pvp(?:@\w+)?$"))
async def pvp_command(message: Message):
    if (
        not message.reply_to_message
        or not message.reply_to_message.from_user
    ):
        await message.answer(
            "⚔️ برای PvP روی پیام بازیکن موردنظر Reply کن "
            "و سپس /pvp را بفرست."
        )
        return

    if message.from_user is None:
        return

    target_id = message.reply_to_message.from_user.id

    if target_id == message.from_user.id:
        await message.answer(
            "⚠️ نمی‌توانی خودت را به PvP دعوت کنی."
        )
        return

    success, result_message = await create_pvp_challenge(
        message.from_user.id,
        target_id,
    )

    prefix = "✅ " if success else "⚠️ "
    await message.answer(prefix + result_message)