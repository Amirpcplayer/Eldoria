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

from services.panel_image_service import show_panel
from middlewares.panel_owner import protect_keyboard

from services.language_service import get_language

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

_EQUIPMENT_TEXT = {
"en": [
("منوی اصلی World Eldoria","World Eldoria Main Menu"),("ماجراجویی تو در اِلدوریا ادامه دارد...","Your adventure in Eldoria continues..."),("تجهیزات قهرمان","Hero Equipment"),("از بخش‌های زیر نوع تجهیزات موردنظر را انتخاب کن:","Choose an equipment category below:"),
("سلاح‌ها","Weapons"),("کلاه‌ها","Helmets"),("زره‌ها","Armor"),("کفش‌ها","Boots"),("انگشترها","Rings"),("گردنبندها","Necklaces"),("معمولی","Common"),("غیرمعمولی","Uncommon"),("کمیاب","Rare"),("حماسی","Epic"),("افسانه‌ای","Legendary"),("اسطوره‌ای","Mythic"),("الهی","Divine"),
("مجهز است","Equipped"),("در صندوقچه است","In Chest"),("قابل استفاده","Usable"),("سطح کافی نیست","Level too low"),("نوع:","Type:"),("کمیابی:","Rarity:"),("سطح موردنیاز:","Required level:"),("سطح قهرمان:","Hero level:"),("وضعیت سطح:","Level status:"),("تعداد:","Quantity:"),("وضعیت:","Status:"),("ویژگی‌های تجهیز","Equipment Stats"),("حمله:","Attack:"),("قدرت جادو:","Magic power:"),("دفاع جادویی:","Magic defense:"),("دفاع:","Defense:"),("سلامتی:","Health:"),("مانا:","Mana:"),("سرعت:","Speed:"),("دقت:","Accuracy:"),("ضربه بحرانی:","Critical hit:"),("بدون توضیحات","No description"),("در حال حاضر هیچ تجهیزی از این نوع در صندوقچه تو وجود ندارد.","You have no equipment of this type in your chest yet."),("تعداد تجهیزات:","Equipment count:"),("برای مشاهده جزئیات، یک تجهیز را انتخاب کن.","Select an item to view its details."),("آمار تجهیزات","Equipment Stats"),("تجهیزات مجهز:","Equipped items:"),("افزایش آمار از تجهیزات","Stats gained from equipment"),("این مقادیر، پاداش آمار تجهیزات مجهز را نشان می‌دهند.","These values show stat bonuses from equipped items."),
("❌ پیام قبلی در دسترس نیست.","❌ Previous message is unavailable."),("❌ حذف پنل قبلی ناموفق بود. لطفاً دوباره تلاش کن.","❌ Could not delete the previous panel. Please try again."),("❌ خطا هنگام حذف پنل قبلی.","❌ Error while deleting the previous panel."),("❌ ارسال پنل تجهیزات ناموفق بود. ترمینال را بررسی کن.","❌ Could not send equipment panel. Check the terminal."),("❌ پیام پنل در دسترس نیست.","❌ Panel message is unavailable."),("❌ اجازه ویرایش این پیام وجود ندارد.","❌ You are not allowed to edit this message."),("❌ خطای غیرمنتظره هنگام ویرایش پنل.","❌ Unexpected error while editing the panel."),("❌ قهرمان پیدا نشد.","❌ Hero not found."),("❌ تجهیز پیدا نشد.","❌ Equipment not found."),("❌ این تجهیز در صندوقچه تو وجود ندارد.","❌ This item is not in your chest."),("❌ قهرمان پیدا نشد. ابتدا شخصیتت را بساز.","❌ Hero not found. Create your character first."),("❌ درخواست نامعتبر است.","❌ Invalid request."),("❌ نوع تجهیزات نامعتبر است.","❌ Invalid equipment type."),("❌ شناسه تجهیز نامعتبر است.","❌ Invalid equipment ID.")
],
"ru": [
("منوی اصلی World Eldoria","Главное меню World Eldoria"),("ماجراجویی تو در اِلدوریا ادامه دارد...","Твоё приключение в Эльдории продолжается..."),("تجهیزات قهرمان","Снаряжение героя"),("از بخش‌های زیر نوع تجهیزات موردنظر را انتخاب کن:","Выбери категорию снаряжения:"),
("سلاح‌ها","Оружие"),("کلاه‌ها","Шлемы"),("زره‌ها","Броня"),("کفش‌ها","Обувь"),("انگشترها","Кольца"),("گردنبندها","Ожерелья"),("معمولی","Обычный"),("غیرمعمولی","Необычный"),("کمیاب","Редкий"),("حماسی","Эпический"),("افسانه‌ای","Легендарный"),("اسطوره‌ای","Мифический"),("الهی","Божественный"),
("مجهز است","Надето"),("در صندوقچه است","В сундуке"),("قابل استفاده","Можно использовать"),("سطح کافی نیست","Недостаточный уровень"),("نوع:","Тип:"),("کمیابی:","Редкость:"),("سطح موردنیاز:","Требуемый уровень:"),("سطح قهرمان:","Уровень героя:"),("وضعیت سطح:","Статус уровня:"),("تعداد:","Количество:"),("وضعیت:","Статус:"),("ویژگی‌های تجهیز","Характеристики снаряжения"),("حمله:","Атака:"),("قدرت جادو:","Сила магии:"),("دفاع جادویی:","Магическая защита:"),("دفاع:","Защита:"),("سلامتی:","Здоровье:"),("مانا:","Мана:"),("سرعت:","Скорость:"),("دقت:","Точность:"),("ضربه بحرانی:","Критический удар:"),("بدون توضیحات","Нет описания"),("در حال حاضر هیچ تجهیزی از این نوع در صندوقچه تو وجود ندارد.","В сундуке пока нет снаряжения этого типа."),("تعداد تجهیزات:","Количество предметов:"),("برای مشاهده جزئیات، یک تجهیز را انتخاب کن.","Выбери предмет, чтобы посмотреть подробности."),("آمار تجهیزات","Характеристики снаряжения"),("تجهیزات مجهز:","Надето предметов:"),("افزایش آمار از تجهیزات","Бонусы от снаряжения"),("این مقادیر، پاداش آمار تجهیزات مجهز را نشان می‌دهند.","Эти значения показывают бонусы от надетого снаряжения."),
("❌ پیام قبلی در دسترس نیست.","❌ Предыдущее сообщение недоступно."),("❌ حذف پنل قبلی ناموفق بود. لطفاً دوباره تلاش کن.","❌ Не удалось удалить предыдущую панель. Попробуй ещё раз."),("❌ خطا هنگام حذف پنل قبلی.","❌ Ошибка при удалении предыдущей панели."),("❌ ارسال پنل تجهیزات ناموفق بود. ترمینال را بررسی کن.","❌ Не удалось отправить панель снаряжения. Проверь терминал."),("❌ پیام پنل در دسترس نیست.","❌ Сообщение панели недоступно."),("❌ اجازه ویرایش این پیام وجود ندارد.","❌ Нет разрешения на редактирование этого сообщения."),("❌ خطای غیرمنتظره هنگام ویرایش پنل.","❌ Непредвиденная ошибка при редактировании панели."),("❌ قهرمان پیدا نشد.","❌ Герой не найден."),("❌ تجهیز پیدا نشد.","❌ Предмет снаряжения не найден."),("❌ این تجهیز در صندوقچه تو وجود ندارد.","❌ Этого предмета нет в сундуке."),("❌ قهرمان پیدا نشد. ابتدا شخصیتت را بساز.","❌ Герой не найден. Сначала создай персонажа."),("❌ درخواست نامعتبر است.","❌ Некорректный запрос."),("❌ نوع تجهیزات نامعتبر است.","❌ Некорректный тип снаряжения."),("❌ شناسه تجهیز نامعتبر است.","❌ Некорректный ID предмета.")
]
}
def _localize_equipment_text(text: str, language: str) -> str:
    if language not in ("en", "ru"): return text
    for source, translated in _EQUIPMENT_TEXT[language]: text = text.replace(source, translated)
    return text

def _localize_equipment_markup(markup, language: str):
    if language not in ("en", "ru") or markup is None: return markup
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    rows = []
    for row in markup.inline_keyboard:
        new_row = []
        for b in row:
            new_row.append(InlineKeyboardButton(text=_localize_equipment_text(b.text, language), callback_data=b.callback_data, url=b.url, web_app=b.web_app, login_url=b.login_url, switch_inline_query=b.switch_inline_query, switch_inline_query_current_chat=b.switch_inline_query_current_chat, callback_game=b.callback_game, pay=b.pay, icon_custom_emoji_id=b.icon_custom_emoji_id, style=b.style))
        rows.append(new_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)



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
    """
    پیام قبلی را حذف و پنل جدید ارسال می‌کند.
    برای ورود به پنل تجهیزات استفاده می‌شود.
    """
    language = await get_language(callback.from_user.id)
    text = _localize_equipment_text(text, language)
    reply_markup = _localize_equipment_markup(reply_markup, language)
    message = callback.message

    if message is None:
        await callback.answer(
            "❌ پیام قبلی در دسترس نیست.",
            show_alert=True,
        )
        return

    try:
        await message.delete()

    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.warning(
            "Could not delete previous panel. "
            "user_id=%s, chat_id=%s, message_id=%s, error=%s",
            callback.from_user.id,
            message.chat.id,
            message.message_id,
            exc,
        )

        await callback.answer(
            "❌ حذف پنل قبلی ناموفق بود. لطفاً دوباره تلاش کن.",
            show_alert=True,
        )
        return

    except Exception:
        logger.exception(
            "Unexpected error deleting previous panel."
        )
        await callback.answer(
            "❌ خطا هنگام حذف پنل قبلی.",
            show_alert=True,
        )
        return

    try:
        # پنل تجهیزات شخصی است؛ همهٔ دکمه‌های آن فقط برای سازنده معتبرند.
        reply_markup = protect_keyboard(reply_markup, callback.from_user.id)
        await message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

    except Exception:
        logger.exception(
            "Could not send equipment panel. user_id=%s",
            callback.from_user.id,
        )
        await callback.answer(
            "❌ ارسال پنل تجهیزات ناموفق بود. ترمینال را بررسی کن.",
            show_alert=True,
        )
        return

    await callback.answer()


async def edit_panel(
    callback: CallbackQuery,
    text: str,
    reply_markup,
) -> None:
    """
    صفحات داخلی تجهیزات را در همان پیام ویرایش می‌کند.
    در صورت ناموفق بودن ویرایش، برای جلوگیری از پنل تکراری
    ابتدا پیام قبلی حذف می‌شود و سپس پنل جایگزین ارسال می‌شود.
    """
    language = await get_language(callback.from_user.id)
    text = _localize_equipment_text(text, language)
    reply_markup = _localize_equipment_markup(reply_markup, language)
    message = callback.message

    if message is None:
        await callback.answer(
            "❌ پیام پنل در دسترس نیست.",
            show_alert=True,
        )
        return

    try:
        # محافظت در سمت پنل، علاوه بر اعتبارسنجی عملیات تجهیزات در سرویس.
        reply_markup = protect_keyboard(reply_markup, callback.from_user.id)
        await message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            await callback.answer()
            return

        logger.warning(
            "Equipment panel edit failed. "
            "user_id=%s, chat_id=%s, message_id=%s, error=%s",
            callback.from_user.id,
            message.chat.id,
            message.message_id,
            exc,
        )

        await send_new_panel(
            callback,
            text,
            reply_markup,
        )
        return

    except TelegramForbiddenError:
        logger.exception(
            "Telegram forbade editing equipment panel."
        )
        await callback.answer(
            "❌ اجازه ویرایش این پیام وجود ندارد.",
            show_alert=True,
        )
        return

    except Exception:
        logger.exception(
            "Unexpected equipment panel edit error."
        )
        await callback.answer(
            "❌ خطای غیرمنتظره هنگام ویرایش پنل.",
            show_alert=True,
        )
        return

    await callback.answer()


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