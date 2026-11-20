from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.enums import ParseMode
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.skill import Skill
from models.character_skill import CharacterSkill

from keyboards.skills import (
    skills_main_keyboard,
    skills_list_keyboard,
    learn_skills_keyboard,
    my_skill_details_keyboard,
    learned_skill_details_keyboard,
    skill_upgrade_list_keyboard,
    skill_upgrade_confirm_keyboard,
)

from services.skill_service import (
    get_skill_power,
    get_skill_mana_cost,
    get_unlocked_skill_slots,
    get_skill_upgrade_info,
    unlock_skill,
    upgrade_skill,
)

from services.panel_image_service import show_panel
from services.language_service import get_language


router = Router()

PANEL_NAME = "skills"


ELEMENT_NAMES = {
    "fire": "🔥 آتش",
    "water": "💧 آب",
    "wind": "🌪️ باد",
    "earth": "🪨 خاک",
    "electro": "⚡ الکترو",
    "ice": "❄️ یخ",
    "light": "☀️ نور",
    "dark": "🌑 تاریکی",
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


# ==================================================
# ابزارهای مشترک
# ==================================================

async def get_character(telegram_id: int):
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )


_SKILL_TRANSLATIONS = {
"en": {
"مهارت‌های قهرمان":"Hero Skills","قدرت‌های جادویی خودت را مدیریت کن.":"Manage your magical abilities.","مهارت‌های من":"My Skills","هنوز هیچ مهارتی یاد نگرفته‌ای.":"You haven't learned any skills yet.","یادگیری مهارت":"Learn Skills","یک مهارت انتخاب کن.":"Choose a skill.","تعداد مهارت‌ها":"Number of skills","قهرمان پیدا نشد.":"Hero not found.","شناسه مهارت نامعتبر است.":"Invalid skill ID.","مهارت پیدا نشد.":"Skill not found.","این مهارت را یاد نگرفته‌ای.":"You haven't learned this skill.","یادگیری مهارت":"Learn Skills","Level قهرمان":"Hero level","اسلات‌های باز":"Unlocked slots","مهارتی که می‌خواهی یاد بگیری انتخاب کن:":"Choose a skill to learn:","قابل انتخاب":"Available","قبلاً یاد گرفته شده":"Already learned","قفل":"Locked","این مهارت هنوز برای قهرمانت باز نشده است.":"This skill is not unlocked for your hero yet.","ارتقای مهارت":"Upgrade Skill","ابتدا از بخش «✨ یادگیری مهارت»":"First learn a skill from “✨ Learn Skills”.","مهارتی که می‌خواهی ارتقا بدهی انتخاب کن:":"Choose a skill to upgrade:","سطح فعلی":"Current level","سطح بعدی":"Next level","قدرت فعلی":"Current power","قدرت بعدی":"Next power","هزینه ارتقا":"Upgrade cost","XP مورد نیاز":"Required XP","Gold مورد نیاز":"Required Gold","موجودی فعلی":"Current balance","آیا می‌خواهی این مهارت را ارتقا بدهی؟":"Do you want to upgrade this skill?","ارتقا با موفقیت انجام شد.":"Skill upgraded successfully.","عنصر":"Element","کمیابی":"Rarity","نوع":"Type","هدف":"Target","بدون توضیحات":"No description","سطح مهارت":"Skill level","قدرت":"Power","شناسه":"ID","معمولی":"Common","غیرمعمولی":"Uncommon","کمیاب":"Rare","حماسی":"Epic","افسانه‌ای":"Legendary","اسطوره‌ای":"Mythic","الهی":"Divine","آتش":"Fire","آب":"Water","باد":"Wind","خاک":"Earth","الکترو":"Electro","یخ":"Ice","نور":"Light","تاریکی":"Dark"},
"ru": {
"مهارت‌های قهرمان":"Навыки героя","قدرت‌های جادویی خودت را مدیریت کن.":"Управляйте магическими способностями.","مهارت‌های من":"Мои навыки","هنوز هیچ مهارتی یاد نگرفته‌ای.":"Вы ещё не изучили навыки.","یادگیری مهارت":"Изучить навык","یک مهارت انتخاب کن.":"Выберите навык.","تعداد مهارت‌ها":"Количество навыков","قهرمان پیدا نشد.":"Герой не найден.","شناسه مهارت نامعتبر است.":"Неверный ID навыка.","مهارت پیدا نشد.":"Навык не найден.","این مهارت را یاد نگرفته‌ای.":"Вы ещё не изучили этот навык.","Level قهرمان":"Уровень героя","اسلات‌های باز":"Открытые ячейки","مهارتی که می‌خواهی یاد بگیری انتخاب کن:":"Выберите навык для изучения:","قابل انتخاب":"Доступно","قبلاً یاد گرفته شده":"Уже изучено","قفل":"Заблокировано","این مهارت هنوز برای قهرمانت باز نشده است.":"Этот навык пока недоступен вашему герою.","ارتقای مهارت":"Улучшить навык","ابتدا از بخش «✨ یادگیری مهارت»":"Сначала изучите навык в разделе «✨ Изучить навык».","مهارتی که می‌خواهی ارتقا بدهی انتخاب کن:":"Выберите навык для улучшения:","سطح فعلی":"Текущий уровень","سطح بعدی":"Следующий уровень","قدرت فعلی":"Текущая сила","قدرت بعدی":"Следующая сила","هزینه ارتقا":"Стоимость улучшения","XP مورد نیاز":"Требуется XP","Gold مورد نیاز":"Требуется золото","موجودی فعلی":"Текущий баланс","آیا می‌خواهی این مهارت را ارتقا بدهی؟":"Хотите улучшить этот навык?","ارتقا با موفقیت انجام شد.":"Навык успешно улучшен.","عنصر":"Стихия","کمیابی":"Редкость","نوع":"Тип","هدف":"Цель","بدون توضیحات":"Без описания","سطح مهارت":"Уровень навыка","قدرت":"Сила","معمولی":"Обычный","غیرمعمولی":"Необычный","کمیاب":"Редкий","حماسی":"Эпический","افسانه‌ای":"Легендарный","اسطوره‌ای":"Мифический","الهی":"Божественный","آتش":"Огонь","آب":"Вода","باد":"Ветер","خاک":"Земля","الکترو":"Электро","یخ":"Лёд","نور":"Свет","تاریکی":"Тьма"}
}

def _translate_skill_text(text: str, language: str) -> str:
    for source, target in _SKILL_TRANSLATIONS.get(language, {}).items():
        text = text.replace(source, target)
    return text


async def render_skills_panel(
    callback: CallbackQuery,
    text: str,
    reply_markup=None,
):
    """
    نمایش پنل مهارت‌ها با مدیریت پیام تصویری یا متنی.
    """
    language = await get_language(callback.from_user.id)
    if language in ("en", "ru"):
        text = _translate_skill_text(text, language)
        if reply_markup is not None and getattr(reply_markup, "inline_keyboard", None):
            rows = []
            for row in reply_markup.inline_keyboard:
                rows.append([button.model_copy(update={"text": _translate_skill_text(button.text, language)}) for button in row])
            reply_markup = reply_markup.model_copy(update={"inline_keyboard": rows})
    return await show_panel(
        callback=callback,
        panel_name=PANEL_NAME,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )


async def show_error(
    callback: CallbackQuery,
    text: str,
):
    language = await get_language(callback.from_user.id)
    await callback.answer(
        _translate_skill_text(text, language),
        show_alert=True,
    )


# ==================================================
# منوی اصلی مهارت‌ها
# ==================================================

@router.callback_query(F.data == "menu:skills")
async def skills_menu_handler(callback: CallbackQuery):
    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await show_error(
            callback,
            "❌ قهرمان پیدا نشد.",
        )
        return

    text = (
        "⚔️ <b>مهارت‌های قهرمان</b>\n\n"
        f"👤 {character.name}\n"
        f"⭐ Level: {character.level}\n\n"
        "قدرت‌های جادویی خودت را مدیریت کن."
    )

    await render_skills_panel(
        callback,
        text,
        skills_main_keyboard(),
    )

    await callback.answer()


# ==================================================
# مهارت‌های من
# ==================================================

@router.callback_query(F.data == "skills:list")
async def skills_list_handler(callback: CallbackQuery):
    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await show_error(
            callback,
            "❌ قهرمان پیدا نشد.",
        )
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CharacterSkill, Skill)
            .join(
                Skill,
                CharacterSkill.skill_id == Skill.id,
            )
            .where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.unlocked.is_(True),
                Skill.is_active.is_(True),
            )
            .order_by(
                CharacterSkill.slot,
                CharacterSkill.id,
            )
        )

        skills = list(result.all())

    if not skills:
        text = (
            "📚 <b>مهارت‌های من</b>\n\n"
            "هنوز هیچ مهارتی یاد نگرفته‌ای.\n\n"
            "✨ از بخش «یادگیری مهارت» "
            "یک مهارت انتخاب کن."
        )

        await render_skills_panel(
            callback,
            text,
            skills_list_keyboard([]),
        )

        await callback.answer()
        return

    buttons = [
        (
            f"✅ {skill.name} • Lv.{character_skill.level}",
            skill.id,
        )
        for character_skill, skill in skills
    ]

    text = (
        "📚 <b>مهارت‌های من</b>\n\n"
        f"⚔️ تعداد مهارت‌ها: {len(skills)}"
    )

    await render_skills_panel(
        callback,
        text,
        skills_list_keyboard(buttons),
    )

    await callback.answer()


# ==================================================
# جزئیات مهارت‌های من
# ==================================================

@router.callback_query(F.data.startswith("skill:details:"))
async def my_skill_details_handler(
    callback: CallbackQuery,
):
    try:
        skill_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await show_error(callback, "❌ شناسه مهارت نامعتبر است.")
        return

    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await show_error(callback, "❌ قهرمان پیدا نشد.")
        return

    async with AsyncSessionLocal() as session:
        skill = await session.scalar(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == skill_id,
                CharacterSkill.unlocked.is_(True),
            )
        )

    if skill is None:
        await show_error(callback, "❌ مهارت پیدا نشد.")
        return

    if character_skill is None:
        await show_error(
            callback,
            "❌ این مهارت را یاد نگرفته‌ای.",
        )
        return

    await show_skill_details(
        callback,
        skill,
        character_skill,
        my_skill_details_keyboard(),
    )


# ==================================================
# یادگیری مهارت
# ==================================================

@router.callback_query(F.data == "skills:learn")
async def skills_learn_handler(callback: CallbackQuery):
    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await show_error(callback, "❌ قهرمان پیدا نشد.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Skill)
            .where(Skill.is_active.is_(True))
            .order_by(
                Skill.unlock_level,
                Skill.id,
            )
        )
        all_skills = list(result.scalars().all())

        owned_result = await session.execute(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.unlocked.is_(True),
            )
        )
        owned_skills = list(owned_result.scalars().all())

    owned_skill_ids = {
        character_skill.skill_id
        for character_skill in owned_skills
    }

    max_slots = get_unlocked_skill_slots(
        character.level
    )
    used_slots = sum(
        1 for character_skill in owned_skills
        if character_skill.slot is not None
    )

    skill_buttons = []

    for skill in all_skills:
        if skill.id in owned_skill_ids:
            skill_buttons.append(
                (skill.name, skill.id, "owned")
            )
            continue

        if skill.unlock_level > character.level:
            skill_buttons.append(
                (
                    f"{skill.name} • Lv.{skill.unlock_level}",
                    skill.id,
                    "locked",
                )
            )
            continue

        skill_buttons.append(
            (skill.name, skill.id, "available")
        )

    text = (
        "✨ <b>یادگیری مهارت</b>\n\n"
        f"⭐ Level قهرمان: {character.level}\n"
        f"⚔️ اسلات‌های باز: {used_slots}/{max_slots}\n\n"
        "مهارتی که می‌خواهی یاد بگیری انتخاب کن:\n\n"
        "🟢 قابل انتخاب\n"
        "✅ قبلاً یاد گرفته شده\n"
        "🔒 قفل"
    )

    await render_skills_panel(
        callback,
        text,
        learn_skills_keyboard(skill_buttons),
    )

    await callback.answer()


# ==================================================
# مهارت قفل‌شده
# ==================================================

@router.callback_query(F.data == "skill:locked")
async def locked_skill_handler(callback: CallbackQuery):
    await callback.answer(
        "🔒 این مهارت هنوز برای قهرمانت باز نشده است.",
        show_alert=True,
    )


# ==================================================
# یادگیری یک مهارت
# ==================================================

@router.callback_query(F.data.startswith("learn:"))
async def learn_skill_handler(callback: CallbackQuery):
    try:
        skill_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await show_error(callback, "❌ شناسه مهارت نامعتبر است.")
        return

    success, message = await unlock_skill(
        callback.from_user.id,
        skill_id,
    )

    if not success:
        await show_error(
            callback,
            message.replace("<b>", "").replace("</b>", ""),
        )
        return

    await render_skills_panel(
        callback,
        message,
        skills_main_keyboard(),
    )

    await callback.answer()


# ==================================================
# جزئیات مهارت در فهرست یادگیری
# ==================================================

@router.callback_query(F.data.startswith("learned:details:"))
async def learned_skill_details_handler(
    callback: CallbackQuery,
):
    try:
        skill_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await show_error(callback, "❌ شناسه مهارت نامعتبر است.")
        return

    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await show_error(callback, "❌ قهرمان پیدا نشد.")
        return

    async with AsyncSessionLocal() as session:
        skill = await session.scalar(
            select(Skill).where(
                Skill.id == skill_id,
                Skill.is_active.is_(True),
            )
        )

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == skill_id,
                CharacterSkill.unlocked.is_(True),
            )
        )

    if skill is None:
        await show_error(callback, "❌ مهارت پیدا نشد.")
        return

    if character_skill is None:
        await show_error(
            callback,
            "❌ این مهارت را یاد نگرفته‌ای.",
        )
        return

    await show_skill_details(
        callback,
        skill,
        character_skill,
        learned_skill_details_keyboard(),
    )


# ==================================================
# فهرست ارتقای مهارت‌ها
# ==================================================

@router.callback_query(F.data == "skills:upgrade")
async def skills_upgrade_list_handler(
    callback: CallbackQuery,
):
    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await show_error(callback, "❌ قهرمان پیدا نشد.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CharacterSkill, Skill)
            .join(
                Skill,
                CharacterSkill.skill_id == Skill.id,
            )
            .where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.unlocked.is_(True),
                Skill.is_active.is_(True),
            )
            .order_by(
                CharacterSkill.slot,
                CharacterSkill.id,
            )
        )

        skills = list(result.all())

    if not skills:
        text = (
            "⬆️ <b>ارتقای مهارت</b>\n\n"
            "❌ هنوز هیچ مهارتی یاد نگرفته‌ای.\n\n"
            "ابتدا از بخش «✨ یادگیری مهارت» "
            "یک مهارت یاد بگیر."
        )

        await render_skills_panel(
            callback,
            text,
            skills_main_keyboard(),
        )

        await callback.answer()
        return

    upgrade_buttons = [
        (
            skill.name,
            skill.id,
            character_skill.level,
        )
        for character_skill, skill in skills
    ]

    text = (
        "⬆️ <b>ارتقای مهارت</b>\n\n"
        "مهارتی که می‌خواهی ارتقا بدهی انتخاب کن:\n\n"
        f"⚔️ تعداد مهارت‌ها: {len(skills)}"
    )

    await render_skills_panel(
        callback,
        text,
        skill_upgrade_list_keyboard(upgrade_buttons),
    )

    await callback.answer()


# ==================================================
# پنل ارتقای یک مهارت
# ==================================================

@router.callback_query(F.data.startswith("skill:upgrade:"))
async def upgrade_skill_handler(
    callback: CallbackQuery,
):
    try:
        skill_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await show_error(callback, "❌ شناسه مهارت نامعتبر است.")
        return

    success, message, info = await get_skill_upgrade_info(
        callback.from_user.id,
        skill_id,
    )

    if not success:
        await show_error(
            callback,
            message.replace("<b>", "").replace("</b>", ""),
        )
        return

    text = (
        "⬆️ <b>ارتقای مهارت</b>\n\n"
        f"✨ {info['skill_name']}\n\n"
        f"⚔️ سطح فعلی: "
        f"{info['current_level']}/{info['max_level']}\n"
        f"➡️ سطح بعدی: "
        f"{info['next_level']}/{info['max_level']}\n\n"
        f"💥 قدرت فعلی: {info['current_power']}\n"
        f"💥 قدرت بعدی: {info['next_power']}\n\n"
        "💰 <b>هزینه ارتقا</b>\n"
        f"✨ XP مورد نیاز: {info['xp_cost']:,}\n"
        f"💰 Gold مورد نیاز: {info['gold_cost']:,}\n\n"
        "🗃 <b>موجودی فعلی</b>\n"
        f"✨ XP: {info['current_xp']:,}\n"
        f"💰 Gold: {info['current_gold']:,}\n\n"
        "آیا می‌خواهی این مهارت را ارتقا بدهی؟"
    )

    await render_skills_panel(
        callback,
        text,
        skill_upgrade_confirm_keyboard(skill_id),
    )

    await callback.answer()


# ==================================================
# تأیید ارتقای مهارت
# ==================================================

@router.callback_query(F.data.startswith("skill:upgrade_confirm:"))
async def confirm_upgrade_skill_handler(
    callback: CallbackQuery,
):
    try:
        skill_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await show_error(callback, "❌ شناسه مهارت نامعتبر است.")
        return

    success, message = await upgrade_skill(
        callback.from_user.id,
        skill_id,
    )

    clean_message = (
        message.replace("<b>", "").replace("</b>", "")
    )

    if not success:
        await show_error(callback, clean_message)
        return

    await render_skills_panel(
        callback,
        clean_message,
        skill_upgrade_list_keyboard([]),
    )

    await callback.answer(
        "✅ ارتقا با موفقیت انجام شد."
    )


# ==================================================
# نمایش مشترک جزئیات مهارت
# ==================================================

async def show_skill_details(
    callback: CallbackQuery,
    skill: Skill,
    character_skill: CharacterSkill,
    keyboard,
):
    level = character_skill.level

    power = get_skill_power(skill, level)
    mana = get_skill_mana_cost(skill, level)

    element = ELEMENT_NAMES.get(
        skill.element,
        skill.element,
    )

    rarity = RARITY_NAMES.get(
        skill.rarity,
        skill.rarity,
    )

    text = (
        f"<b>{skill.name}</b>\n\n"
        f"🌟 عنصر: {element}\n"
        f"💎 کمیابی: {rarity}\n"
        f"📖 نوع: {skill.skill_type}\n"
        f"🎯 هدف: {skill.target_type}\n\n"
        f"📝 {skill.description or 'بدون توضیحات'}\n\n"
        f"⚔️ سطح مهارت: {level}/{skill.max_level}\n"
        f"💥 قدرت: {power}\n"
        f"💧 Mana: {mana}\n"
        f"⏳ Cooldown: {skill.cooldown} ثانیه"
    )

    await render_skills_panel(
        callback,
        text,
        keyboard,
    )

    await callback.answer()