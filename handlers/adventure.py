from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.adventure import (
    adventure_main_keyboard,
    adventure_areas_keyboard,
    adventure_area_keyboard,
    adventure_encounter_keyboard,
    adventure_enemies_keyboard,
    adventure_enemy_keyboard,
)
from keyboards.main_menu import main_menu_keyboard
from services.adventure_service import (
    get_character,
    get_active_areas,
    get_area,
    get_area_enemies,
    get_enemy,
    is_area_unlocked,
)

router = Router()


async def show_adventure_menu(
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
        "🗺️ <b>ماجراجویی</b>\n\n"
        "🌌 در سرزمین‌های اِلدوریا به ماجراجویی بپرداز.\n\n"
        f"⭐ سطح قهرمان: {character.level}\n\n"
        "یک بخش را انتخاب کن:",
        reply_markup=adventure_main_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(
    F.data == "menu:adventure"
)
async def adventure_menu(
    callback: CallbackQuery,
):
    await show_adventure_menu(callback)


@router.callback_query(
    F.data == "adventure:menu"
)
async def adventure_menu_back(
    callback: CallbackQuery,
):
    await show_adventure_menu(callback)


@router.callback_query(
    F.data == "adventure:areas"
)
async def adventure_areas(
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

    areas = await get_active_areas()

    if not areas:
        await callback.message.edit_text(
            "🌲 <b>مناطق ماجراجویی</b>\n\n"
            "📦 در حال حاضر هیچ منطقه‌ای فعال نیست.",
            reply_markup=adventure_main_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    text = (
        "🌲 <b>مناطق ماجراجویی</b>\n\n"
        f"⭐ سطح فعلی تو: {character.level}\n\n"
        "🔓 منطقه‌ای را برای مشاهده جزئیات انتخاب کن."
    )

    await callback.message.edit_text(
        text,
        reply_markup=adventure_areas_keyboard(areas),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("adventure:area:")
)
async def adventure_area_details(
    callback: CallbackQuery,
):
    try:
        area_id = int(
            callback.data.split(":")[2]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "❌ منطقه نامعتبر است.",
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

    area = await get_area(area_id)

    if area is None:
        await callback.answer(
            "❌ منطقه پیدا نشد.",
            show_alert=True,
        )
        return

    unlocked = is_area_unlocked(
        character,
        area,
    )

    status = (
        "🔓 قابل ورود"
        if unlocked
        else "🔒 قفل"
    )

    text = (
        f"{area.name}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📖 {area.description}\n\n"
        f"{status}\n"
        f"⭐ سطح پیشنهادی: {area.recommended_level}\n"
        f"📈 محدوده سطح: {area.min_level} تا {area.max_level}\n\n"
        "🎁 <b>پاداش پایه</b>\n"
        f"✨ XP: +{area.xp_reward}\n"
        f"💰 Gold: +{area.gold_reward}"
    )

    if not unlocked:
        text += (
            "\n\n"
            f"🔒 برای ورود حداقل Level {area.min_level} "
            "لازم است."
        )

    await callback.message.edit_text(
        text,
        reply_markup=adventure_area_keyboard(
            area.id,
            unlocked,
        ),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("adventure:start:")
)
async def adventure_start(
    callback: CallbackQuery,
):
    try:
        area_id = int(
            callback.data.split(":")[2]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "❌ منطقه نامعتبر است.",
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

    area = await get_area(area_id)

    if area is None:
        await callback.answer(
            "❌ منطقه پیدا نشد.",
            show_alert=True,
        )
        return

    if not is_area_unlocked(
        character,
        area,
    ):
        await callback.answer(
            f"🔒 برای ورود به این منطقه "
            f"حداقل Level {area.min_level} لازم است.",
            show_alert=True,
        )
        return

    enemies = await get_area_enemies(
        area.id
    )

    if not enemies:
        await callback.message.edit_text(
            f"⚔️ <b>{area.name}</b>\n\n"
            "🌌 وارد منطقه شدی.\n\n"
            "📦 در حال حاضر هیچ دشمن فعالی "
            "در این منطقه وجود ندارد.",
            reply_markup=adventure_area_keyboard(
                area.id,
                True,
            ),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"⚔️ <b>{area.name}</b>\n\n"
        "🌌 وارد منطقه شدی.\n\n"
        "👾 دشمنان این منطقه را مشاهده کن "
        "و حریف خود را انتخاب کن.",
        reply_markup=adventure_encounter_keyboard(
            area.id,
        ),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("adventure:enemies:")
)
async def adventure_enemies(
    callback: CallbackQuery,
):
    try:
        area_id = int(
            callback.data.split(":")[2]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "❌ منطقه نامعتبر است.",
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

    area = await get_area(area_id)

    if area is None:
        await callback.answer(
            "❌ منطقه پیدا نشد.",
            show_alert=True,
        )
        return

    if not is_area_unlocked(
        character,
        area,
    ):
        await callback.answer(
            "🔒 این منطقه برای تو قفل است.",
            show_alert=True,
        )
        return

    enemies = await get_area_enemies(
        area.id
    )

    if not enemies:
        await callback.message.edit_text(
            f"👾 <b>دشمنان {area.name}</b>\n\n"
            "در حال حاضر دشمنی در این منطقه ثبت نشده است.",
            reply_markup=adventure_area_keyboard(
                area.id,
                True,
            ),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"👾 <b>دشمنان {area.name}</b>\n\n"
        "حریف موردنظر را انتخاب کن:",
        reply_markup=adventure_enemies_keyboard(
            enemies,
            area.id,
        ),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("adventure:enemy:")
)
async def adventure_enemy_details(
    callback: CallbackQuery,
):
    try:
        enemy_id = int(
            callback.data.split(":")[2]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "❌ دشمن نامعتبر است.",
            show_alert=True,
        )
        return

    enemy = await get_enemy(enemy_id)

    if enemy is None:
        await callback.answer(
            "❌ دشمن پیدا نشد.",
            show_alert=True,
        )
        return

    area = await get_area(enemy.area_id)

    if area is None:
        await callback.answer(
            "❌ منطقه دشمن پیدا نشد.",
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

    if not is_area_unlocked(
        character,
        area,
    ):
        await callback.answer(
            "🔒 این منطقه برای تو قفل است.",
            show_alert=True,
        )
        return

    text = (
        f"👾 <b>{enemy.name}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📖 {enemy.description}\n\n"
        f"⭐ Level: {enemy.level}\n"
        f"❤️ HP: {enemy.hp}\n"
        f"⚔️ Attack: {enemy.attack}\n"
        f"🛡️ Defense: {enemy.defense}\n\n"
        "🎁 <b>پاداش پیروزی</b>\n"
        f"✨ XP: +{enemy.xp_reward}\n"
        f"💰 Gold: +{enemy.gold_reward}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=adventure_enemy_keyboard(
            enemy.id,
            area.id,
        ),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(
    F.data == "adventure:back"
)
async def adventure_back(
    callback: CallbackQuery,
):
    await callback.message.edit_text(
        "🎮 <b>منوی اصلی World Eldoria</b>\n\n"
        "🌌 ماجراجویی تو در اِلدوریا ادامه دارد...",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )

    await callback.answer()