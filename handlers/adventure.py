from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.monster import Monster

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

from services.panel_image_service import show_panel


router = Router()


async def _adventure_drop_preview(enemy, character) -> str:
    """Describe every item that can drop from this enemy, matching the real loot logic."""
    family = "default"
    if enemy.monster_id:
        async with AsyncSessionLocal() as session:
            monster = await session.scalar(
                select(Monster).where(Monster.id == enemy.monster_id)
            )
        if monster:
            family = (monster.family or "").lower()
            variant = (monster.variant or "").lower()
            if any(token in family or token in variant for token in ("dragon", "drake")):
                family = "dragon"

    family_drops = {
        "wolf": ("🦴 پنجهٔ گرگ", 0.42),
        "goblin": ("⛏️ تکه‌آهن گابلین", 0.36),
        "golem": ("🗃 سنگ جادویی", 0.30),
        "dragon": ("🔥 فلس اژدها", 0.16),
        "default": ("🌿 گیاه اِلدوریا", 0.24),
    }
    family_name, family_chance = family_drops.get(family, family_drops["default"])
    luck_bonus = 1 + min(int(getattr(character, "luck", 0) or 0), 100) / 250
    family_chance = min(0.8, family_chance * luck_bonus)

    # The real reward logic chooses one of these five materials at random per fight.
    gathering_drops = [
        ("🪵 چوب اِلدوری", 0.12),
        ("⛓️ سنگ آهن", 0.12),
        ("💎 کریستال جادویی", 0.055),
        ("🌿 گیاه اِلدوریا", 0.16),
        ("🗃 سنگ جادویی", 0.08 if family == "golem" else 0.025),
    ]
    lines = [
        "🎁 <b>غنیمت‌های احتمالی این مبارزه</b>",
        f"• {family_name} — احتمال پایه: حدود {family_chance * 100:.1f}٪",
        "",
        "🔎 <b>مواد جانبی</b> (در هر مبارزه یکی انتخاب می‌شود):",
    ]
    for name, chance in gathering_drops:
        actual_chance = chance / len(gathering_drops)
        lines.append(f"• {name} — حدود {actual_chance * 100:.1f}٪")
    lines.append("")
    lines.append("💡 شانس‌ها پایه هستند؛ طومار کاوشگر و شانس قهرمان می‌توانند شانس دریافت را افزایش دهند.")
    return "\\n".join(lines)


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

    text = (
        "🗺️ <b>ماجراجویی</b>\n\n"
        "🌌 در سرزمین‌های اِلدوریا به ماجراجویی بپرداز.\n\n"
        f"⭐ سطح قهرمان: {character.level}\n\n"
        "یک بخش را انتخاب کن:"
    )

    await show_panel(
        callback=callback,
        panel_name="adventure",
        text=text,
        reply_markup=adventure_main_keyboard(),
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
        text = (
            "🌲 <b>مناطق ماجراجویی</b>\n\n"
            "🗃 در حال حاضر هیچ منطقه‌ای فعال نیست."
        )

        await show_panel(
            callback=callback,
            panel_name="adventure",
            text=text,
            reply_markup=adventure_main_keyboard(),
        )

        await callback.answer()
        return

    text = (
        "🌲 <b>مناطق ماجراجویی</b>\n\n"
        f"⭐ سطح فعلی تو: {character.level}\n\n"
        "🔓 منطقه‌ای را برای مشاهده جزئیات انتخاب کن."
    )

    await show_panel(
        callback=callback,
        panel_name="adventure",
        text=text,
        reply_markup=adventure_areas_keyboard(areas),
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

    await show_panel(
        callback=callback,
        panel_name="adventure",
        text=text,
        reply_markup=adventure_area_keyboard(
            area.id,
            unlocked,
        ),
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
        text = (
            f"⚔️ <b>{area.name}</b>\n\n"
            "🌌 وارد منطقه شدی.\n\n"
            "🗃 در حال حاضر هیچ دشمن فعالی "
            "در این منطقه وجود ندارد."
        )

        await show_panel(
            callback=callback,
            panel_name="adventure",
            text=text,
            reply_markup=adventure_area_keyboard(
                area.id,
                True,
            ),
        )

        await callback.answer()
        return

    text = (
        f"⚔️ <b>{area.name}</b>\n\n"
        "🌌 وارد منطقه شدی.\n\n"
        " دشمنان این منطقه را مشاهده کن "
        "و حریف خود را انتخاب کن."
    )

    await show_panel(
        callback=callback,
        panel_name="adventure",
        text=text,
        reply_markup=adventure_encounter_keyboard(
            area.id,
        ),
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
        text = (
            f" <b>دشمنان {area.name}</b>\n\n"
            "در حال حاضر دشمنی در این منطقه ثبت نشده است."
        )

        await show_panel(
            callback=callback,
            panel_name="adventure",
            text=text,
            reply_markup=adventure_area_keyboard(
                area.id,
                True,
            ),
        )

        await callback.answer()
        return

    text = (
        f" <b>دشمنان {area.name}</b>\n\n"
        "حریف موردنظر را انتخاب کن:"
    )

    await show_panel(
        callback=callback,
        panel_name="adventure",
        text=text,
        reply_markup=adventure_enemies_keyboard(
            enemies,
            area.id,
        ),
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

    drop_preview = await _adventure_drop_preview(enemy, character)
    text = (
        f"⚔️ <b>{enemy.name}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📖 {enemy.description}\n\n"
        f"⭐ Level: {enemy.level}\n"
        f"❤️ HP: {enemy.hp:,}\n"
        f"⚔️ Attack: {enemy.attack:,}\n"
        f"🛡️ Defense: {enemy.defense:,}\n\n"
        "🎁 <b>پاداش پیروزی</b>\n"
        f"✨ XP: +{enemy.xp_reward:,}\n"
        f"💰 Gold: +{enemy.gold_reward:,}\n\n"
        f"{drop_preview}"
    )

    await show_panel(
        callback=callback,
        panel_name="adventure",
        text=text,
        reply_markup=adventure_enemy_keyboard(
            enemy.id,
            area.id,
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data == "adventure:back"
)
async def adventure_back(
    callback: CallbackQuery,
):
    text = (
        "🎮 <b>منوی اصلی World Eldoria</b>\n\n"
        "🌌 ماجراجویی تو در اِلدوریا ادامه دارد..."
    )

    await show_panel(
        callback=callback,
        panel_name="main_menu",
        text=text,
        reply_markup=main_menu_keyboard(),
    )

    await callback.answer()