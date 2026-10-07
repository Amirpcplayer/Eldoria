from aiogram import Router
from aiogram.types import CallbackQuery

from keyboards.equipment import (
    equipment_main_keyboard,
    equipment_list_keyboard,
    equipment_details_keyboard,
)

from keyboards.main_menu import main_menu_keyboard

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


router = Router()


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


def get_rarity_name(
    rarity: str,
) -> str:

    return RARITY_NAMES.get(
        rarity,
        rarity,
    )


def get_equipment_type_title(
    equipment_type: str,
) -> str:

    return EQUIPMENT_TYPE_NAMES.get(
        equipment_type,
        equipment_type,
    )


async def show_equipment_details(
    callback: CallbackQuery,
    equipment_id: int,
):
    telegram_id = callback.from_user.id

    character = await get_character(
        telegram_id
    )

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    equipment = await get_equipment(
        equipment_id
    )

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

    type_name = get_equipment_type_title(
        equipment_type
    )

    rarity = get_rarity_name(
        equipment.rarity
    )

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
        f"📦 نوع: {type_name}\n"
        f"💎 کمیابی: {rarity}\n"
        f"⭐ سطح موردنیاز: "
        f"{equipment.required_level}\n"
        f"🧙 سطح قهرمان: "
        f"{character.level}\n"
        f"📌 وضعیت سطح: {level_status}\n"
        f"🔢 تعداد: ×{character_equipment.quantity}\n"
        f"📍 وضعیت: {status}\n\n"
        "📊 <b>ویژگی‌های تجهیز</b>\n"
        f"⚔️ Attack: +{equipment.attack}\n"
        f"🔮 Magic Power: +{equipment.magic_power}\n"
        f"🛡️ Defense: +{equipment.defense}\n"
        f"🔰 Magic Defense: +{equipment.magic_defense}\n"
        f"❤️ HP: +{equipment.hp}\n"
        f"💧 Mana: +{equipment.mana}\n"
        f"💨 Speed: +{equipment.speed}\n"
        f"🎯 Accuracy: +{equipment.accuracy}\n"
        f"💥 Critical: +{equipment.critical}%\n\n"
        f"📝 {equipment.description or 'بدون توضیحات'}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=equipment_details_keyboard(
            equipment.id,
            character_equipment.equipped,
            equipment_type,
        ),
    )

    await callback.answer()


@router.callback_query(
    lambda callback: callback.data == "menu:equipment"
)
async def equipment_menu(
    callback: CallbackQuery,
):

    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "🛡️ <b>تجهیزات قهرمان</b>\n\n"
        "از بخش‌های زیر نوع تجهیزات موردنظر را انتخاب کن:",
        reply_markup=equipment_main_keyboard(),
    )

    await callback.answer()


@router.callback_query(
    lambda callback: callback.data == "equipment:menu"
)
async def equipment_menu_back(
    callback: CallbackQuery,
):

    await equipment_menu(
        callback
    )


@router.callback_query(
    lambda callback: callback.data.startswith(
        "equipment:list:"
    )
)
async def equipment_list_handler(
    callback: CallbackQuery,
):

    equipment_type = callback.data.split(":")[2]

    if equipment_type not in EQUIPMENT_TYPE_NAMES:
        await callback.answer(
            "❌ نوع تجهیزات نامعتبر است.",
            show_alert=True,
        )
        return

    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    all_equipment = await get_character_equipments(
        callback.from_user.id
    )

    equipment_list = [
        item
        for item in all_equipment
        if item[1].equipment_type == equipment_type
    ]

    type_name = get_equipment_type_title(
        equipment_type
    )

    if not equipment_list:

        await callback.message.edit_text(
            f"{type_name}\n\n"
            "📦 در حال حاضر هیچ تجهیزی از این نوع "
            "در صندوقچه تو وجود ندارد.",
            reply_markup=equipment_list_keyboard(
                [],
                equipment_type,
            ),
        )

        await callback.answer()
        return

    text = (
        f"{type_name}\n\n"
        f"📦 تعداد تجهیزات: "
        f"{len(equipment_list)}\n\n"
        "برای مشاهده جزئیات، یک تجهیز را انتخاب کن."
    )

    await callback.message.edit_text(
        text,
        reply_markup=equipment_list_keyboard(
            equipment_list,
            equipment_type,
        ),
    )

    await callback.answer()


@router.callback_query(
    lambda callback: callback.data.startswith(
        "equipment:item:"
    )
)
async def equipment_details_handler(
    callback: CallbackQuery,
):

    equipment_id = int(
        callback.data.split(":")[2]
    )

    await show_equipment_details(
        callback,
        equipment_id,
    )


@router.callback_query(
    lambda callback: callback.data.startswith(
        "equipment:equip:"
    )
)
async def equipment_equip_handler(
    callback: CallbackQuery,
):

    equipment_id = int(
        callback.data.split(":")[2]
    )

    success, message = await equip_equipment(
        callback.from_user.id,
        equipment_id,
    )

    if not success:

        clean_message = (
            message
            .replace("<b>", "")
            .replace("</b>", "")
        )

        await callback.answer(
            clean_message,
            show_alert=True,
        )
        return

    await show_equipment_details(
        callback,
        equipment_id,
    )

    await callback.answer(
        "✅ تجهیز با موفقیت مجهز شد."
    )


@router.callback_query(
    lambda callback: callback.data.startswith(
        "equipment:unequip:"
    )
)
async def equipment_unequip_handler(
    callback: CallbackQuery,
):

    equipment_id = int(
        callback.data.split(":")[2]
    )

    success, message = await unequip_equipment(
        callback.from_user.id,
        equipment_id,
    )

    if not success:

        clean_message = (
            message
            .replace("<b>", "")
            .replace("</b>", "")
        )

        await callback.answer(
            clean_message,
            show_alert=True,
        )
        return

    await show_equipment_details(
        callback,
        equipment_id,
    )

    await callback.answer(
        "✅ تجهیز از حالت استفاده خارج شد."
    )


@router.callback_query(
    lambda callback: callback.data == "equipment:stats"
)
async def equipment_stats_handler(
    callback: CallbackQuery,
):

    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    stats = await get_equipment_stats(
        callback.from_user.id
    )

    equipped = await get_equipped_equipments(
        callback.from_user.id
    )

    text = (
        "📊 <b>آمار تجهیزات</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🛡️ تجهیزات مجهز: "
        f"{len(equipped)}\n\n"
        "⚔️ <b>Bonusهای تجهیزات</b>\n"
        f"⚔️ Attack: +{stats['attack']}\n"
        f"🔮 Magic Power: +{stats['magic_power']}\n"
        f"🛡️ Defense: +{stats['defense']}\n"
        f"🔰 Magic Defense: +{stats['magic_defense']}\n"
        f"❤️ HP: +{stats['hp']}\n"
        f"💧 Mana: +{stats['mana']}\n"
        f"💨 Speed: +{stats['speed']}\n"
        f"🎯 Accuracy: +{stats['accuracy']}\n"
        f"💥 Critical: +{stats['critical']}%\n\n"
        "این مقادیر به آمار پایه قهرمان اضافه می‌شوند."
    )

    await callback.message.edit_text(
        text,
        reply_markup=equipment_main_keyboard(),
    )

    await callback.answer()


@router.callback_query(
    lambda callback: callback.data == "equipment:back"
)
async def equipment_back_handler(
    callback: CallbackQuery,
):

    await callback.message.edit_text(
        "🎮 <b>منوی اصلی World Eldoria</b>\n\n"
        "🌌 ماجراجویی تو در اِلدوریا ادامه دارد...",
        reply_markup=main_menu_keyboard(),
    )

    await callback.answer()