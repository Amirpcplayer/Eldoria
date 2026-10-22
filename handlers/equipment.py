from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
)
from aiogram.types import CallbackQuery

from keyboards.equipment import (
    equipment_main_keyboard,
    equipment_list_keyboard,
    equipment_details_keyboard,
)
from keyboards.main_menu import main_menu_keyboard

from services.panel_image_service import show_panel, replace_panel_with_text
from middlewares.panel_owner import protect_keyboard

from services.equipment_service import (
    get_character,
    get_equipment,
    get_character_equipment,
    get_character_equipments,
    get_equipped_equipments,
    equip_equipment,
    unequip_equipment,
    get_equipment_stats,
)


router = Router(name="equipment")
logger = logging.getLogger(__name__)


EQUIPMENT_TYPE_NAMES = {
    "weapon": "⚔️ سلاح‌ها",
    "helmet": "🪖 کلاه‌ها",
    "armor": "🛡️ زره‌ها",
    "boots": "👢 کفش‌ها",
    "ring": "💍 انگشترها",
    "necklace": "📿 گردنبندها",
}

RARITY_NAMES = {
    "common": "⚪ معمولی",
    "uncommon": "🟢 غیرمعمولی",
    "rare": "🔵 کمیاب",
    "epic": "🟣 حماسی",
    "legendary": "🟠 افسانه‌ای",
    "mythic": "🔴 اسطوره‌ای",
    "divine": "✨ الهی",
}


MAIN_MENU_TEXT = (
    "🎮 <b>منوی اصلی World Eldoria</b>\n\n"
    "🌌 ماجراجویی تو در اِلدوریا ادامه دارد..."
)


EQUIPMENT_MENU_TEXT = (
    "🛡️ <b>تجهیزات قهرمان</b>\n\n"
    "از بخش‌های زیر نوع تجهیزات موردنظر را انتخاب کن:"
)


def get_rarity_name(rarity: str) -> str:
    return RARITY_NAMES.get(rarity, rarity)


def get_equipment_type_title(equipment_type: str) -> str:
    return EQUIPMENT_TYPE_NAMES.get(
        equipment_type,
        equipment_type,
    )


async def send_new_panel(
    callback: CallbackQuery,
    text: str,
    reply_markup,
) -> None:
    """Equipment entry uses the same editable text panel as every other menu."""
    await replace_panel_with_text(
        callback=callback,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


async def edit_panel(
    callback: CallbackQuery,
    text: str,
    reply_markup,
) -> None:
    """Edit the existing equipment panel, replacing only if Telegram requires it."""
    await replace_panel_with_text(
        callback=callback,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )

async def show_equipment_details(
    callback: CallbackQuery,
    equipment_id: int,
) -> None:
    telegram_id = callback.from_user.id

    character = await get_character(telegram_id)

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    equipment = await get_equipment(equipment_id)

    if equipment is None:
        await callback.answer(
            "❌ تجهیز پیدا نشد.",
            show_alert=True,
        )
        return

    character_equipment = await get_character_equipment(
        telegram_id,
        equipment_id,
    )

    if character_equipment is None:
        await callback.answer(
            "❌ این تجهیز در صندوقچه تو وجود ندارد.",
            show_alert=True,
        )
        return

    equipment_type = equipment.equipment_type

    status = (
        "🟢 مجهز است"
        if character_equipment.equipped
        else "⚪ در صندوقچه است"
    )

    level_status = (
        "✅ قابل استفاده"
        if character.level >= equipment.required_level
        else "🔒 سطح کافی نیست"
    )

    text = (
        f"{equipment.name}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🗃 نوع: {get_equipment_type_title(equipment_type)}\n"
        f"💎 کمیابی: {get_rarity_name(equipment.rarity)}\n"
        f"⭐ سطح موردنیاز: {equipment.required_level}\n"
        f"🧙 سطح قهرمان: {character.level}\n"
        f"📌 وضعیت سطح: {level_status}\n"
        f"🔢 تعداد: ×{character_equipment.quantity}\n"
        f"📍 وضعیت: {status}\n\n"
        "📊 <b>ویژگی‌های تجهیز</b>\n"
        f"⚔️ حمله: +{equipment.attack}\n"
        f"🔮 قدرت جادو: +{equipment.magic_power}\n"
        f"🛡️ دفاع: +{equipment.defense}\n"
        f"🔰 دفاع جادویی: +{equipment.magic_defense}\n"
        f"❤️ سلامتی: +{equipment.hp}\n"
        f"💧 مانا: +{equipment.mana}\n"
        f"💨 سرعت: +{equipment.speed}\n"
        f"🎯 دقت: +{equipment.accuracy}\n"
        f"💥 ضربه بحرانی: +{equipment.critical}%\n\n"
        f"📝 {equipment.description or 'بدون توضیحات'}"
    )

    await edit_panel(
        callback,
        text,
        equipment_details_keyboard(
            equipment.id,
            character_equipment.equipped,
            equipment_type,
        ),
    )


@router.callback_query(F.data == "menu:equipment")
async def equipment_menu(callback: CallbackQuery) -> None:
    logger.info(
        "Equipment menu callback received from user %s",
        callback.from_user.id,
    )

    character = await get_character(callback.from_user.id)

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد. ابتدا شخصیتت را بساز.",
            show_alert=True,
        )
        return

    await send_new_panel(
        callback,
        EQUIPMENT_MENU_TEXT,
        equipment_main_keyboard(),
    )


@router.callback_query(F.data == "equipment:menu")
async def equipment_menu_back(callback: CallbackQuery) -> None:
    character = await get_character(callback.from_user.id)

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    await edit_panel(
        callback,
        EQUIPMENT_MENU_TEXT,
        equipment_main_keyboard(),
    )


@router.callback_query(F.data.startswith("equipment:list:"))
async def equipment_list_handler(
    callback: CallbackQuery,
) -> None:
    parts = (callback.data or "").split(":")

    if len(parts) != 3:
        await callback.answer(
            "❌ درخواست نامعتبر است.",
            show_alert=True,
        )
        return

    equipment_type = parts[2]

    if equipment_type not in EQUIPMENT_TYPE_NAMES:
        await callback.answer(
            "❌ نوع تجهیزات نامعتبر است.",
            show_alert=True,
        )
        return

    telegram_id = callback.from_user.id
    character = await get_character(telegram_id)

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    all_equipment = await get_character_equipments(
        telegram_id
    )

    equipment_list = [
        item
        for item in all_equipment
        if item[1].equipment_type == equipment_type
    ]

    type_name = get_equipment_type_title(equipment_type)

    if not equipment_list:
        await edit_panel(
            callback,
            (
                f"{type_name}\n\n"
                "🗃 در حال حاضر هیچ تجهیزی از این نوع "
                "در صندوقچه تو وجود ندارد."
            ),
            equipment_list_keyboard(
                [],
                equipment_type,
            ),
        )
        return

    text = (
        f"{type_name}\n\n"
        f"🗃 تعداد تجهیزات: {len(equipment_list)}\n\n"
        "برای مشاهده جزئیات، یک تجهیز را انتخاب کن."
    )

    await edit_panel(
        callback,
        text,
        equipment_list_keyboard(
            equipment_list,
            equipment_type,
        ),
    )


@router.callback_query(F.data.startswith("equipment:item:"))
async def equipment_details_handler(
    callback: CallbackQuery,
) -> None:
    parts = (callback.data or "").split(":")

    if len(parts) != 3 or not parts[2].isdigit():
        await callback.answer(
            "❌ شناسه تجهیز نامعتبر است.",
            show_alert=True,
        )
        return

    await show_equipment_details(
        callback,
        int(parts[2]),
    )


@router.callback_query(F.data.startswith("equipment:equip:"))
async def equipment_equip_handler(
    callback: CallbackQuery,
) -> None:
    parts = (callback.data or "").split(":")

    if len(parts) != 3 or not parts[2].isdigit():
        await callback.answer(
            "❌ شناسه تجهیز نامعتبر است.",
            show_alert=True,
        )
        return

    equipment_id = int(parts[2])

    success, result_message = await equip_equipment(
        callback.from_user.id,
        equipment_id,
    )

    if not success:
        await callback.answer(
            result_message.replace("<b>", "").replace("</b>", ""),
            show_alert=True,
        )
        return

    await show_equipment_details(
        callback,
        equipment_id,
    )


@router.callback_query(F.data.startswith("equipment:unequip:"))
async def equipment_unequip_handler(
    callback: CallbackQuery,
) -> None:
    parts = (callback.data or "").split(":")

    if len(parts) != 3 or not parts[2].isdigit():
        await callback.answer(
            "❌ شناسه تجهیز نامعتبر است.",
            show_alert=True,
        )
        return

    equipment_id = int(parts[2])

    success, result_message = await unequip_equipment(
        callback.from_user.id,
        equipment_id,
    )

    if not success:
        await callback.answer(
            result_message.replace("<b>", "").replace("</b>", ""),
            show_alert=True,
        )
        return

    await show_equipment_details(
        callback,
        equipment_id,
    )


@router.callback_query(F.data == "equipment:stats")
async def equipment_stats_handler(
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

    stats = await get_equipment_stats(telegram_id)
    equipped = await get_equipped_equipments(telegram_id)

    text = (
        "📊 <b>آمار تجهیزات</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🛡️ تجهیزات مجهز: {len(equipped)}\n\n"
        "⚔️ <b>افزایش آمار از تجهیزات</b>\n"
        f"⚔️ حمله: +{stats['attack']}\n"
        f"🔮 قدرت جادو: +{stats['magic_power']}\n"
        f"🛡️ دفاع: +{stats['defense']}\n"
        f"🔰 دفاع جادویی: +{stats['magic_defense']}\n"
        f"❤️ سلامتی: +{stats['hp']}\n"
        f"💧 مانا: +{stats['mana']}\n"
        f"💨 سرعت: +{stats['speed']}\n"
        f"🎯 دقت: +{stats['accuracy']}\n"
        f"💥 ضربه بحرانی: +{stats['critical']}%\n\n"
        "این مقادیر، پاداش آمار تجهیزات مجهز را نشان می‌دهند."
    )

    await edit_panel(
        callback,
        text,
        equipment_main_keyboard(),
    )


@router.callback_query(F.data == "equipment:back")
async def equipment_back_handler(
    callback: CallbackQuery,
) -> None:
    await show_panel(
        callback=callback,
        panel_name="main_menu",
        text=MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(),
    )

    await callback.answer()