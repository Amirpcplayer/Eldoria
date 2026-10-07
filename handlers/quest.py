from aiogram import Router
from aiogram.types import CallbackQuery

from keyboards.quest import (
    quest_main_keyboard,
    quest_list_keyboard,
    quest_detail_keyboard,
    quest_current_list_keyboard,
)

from services.quest_service import (
    QUEST_CATEGORIES,
    QUEST_STATUS,
    OBJECTIVE_TYPES,
    ensure_character_quests,
    get_character_quests,
    get_character_quest,
    get_quest,
    claim_quest,
)


router = Router()


# ============================================================
# Helpers
# ============================================================

def format_quest_progress(
    progress: int,
    required_amount: int,
) -> str:
    required_amount = max(1, required_amount)
    progress = max(0, min(progress, required_amount))

    percentage = int((progress / required_amount) * 100)

    bar_size = 10
    filled = int((percentage / 100) * bar_size)
    empty = bar_size - filled

    bar = "🟩" * filled + "⬜" * empty

    return (
        f"{bar} {percentage}%\n"
        f"📊 {progress} / {required_amount}"
    )


def format_quest_status(status: str) -> str:
    return QUEST_STATUS.get(
        status,
        "❔ نامشخص",
    )


def format_objective_type(objective_type: str) -> str:
    return OBJECTIVE_TYPES.get(
        objective_type,
        objective_type,
    )


def format_reward(quest) -> str:
    rewards = []

    if quest.reward_xp > 0:
        rewards.append(f"✨ {quest.reward_xp:,} XP")

    if quest.reward_skill_xp > 0:
        rewards.append(f"🔮 {quest.reward_skill_xp:,} Skill XP")

    if quest.reward_gold > 0:
        rewards.append(f"💰 {quest.reward_gold:,} Gold")

    if quest.reward_equipment_id is not None:
        rewards.append("🛡️ تجهیزات")

    if not rewards:
        return "🎁 بدون پاداش"

    return "\n".join(
        f"• {reward}"
        for reward in rewards
    )


# ============================================================
# Quest Main Menu
# ============================================================

@router.callback_query(lambda callback: callback.data == "menu:quest")
async def open_quest_menu(callback: CallbackQuery):
    await callback.answer()

    text = (
        "📜 <b>مأموریت‌های اِلدوریا</b>\n\n"
        "در این بخش می‌توانی مأموریت‌های خود را مشاهده و "
        "پاداش مأموریت‌های تکمیل‌شده را دریافت کنی.\n\n"
        "📖 داستانی\n"
        "مأموریت‌های اصلی و داستانی جهان اِلدوریا\n\n"
        "📅 روزانه\n"
        "مأموریت‌هایی که هر روز قابل انجام هستند\n\n"
        "🏆 دستاوردها\n"
        "اهداف مهم و بلندمدت قهرمان"
    )

    await callback.message.edit_text(
        text,
        reply_markup=quest_main_keyboard(),
    )


# ============================================================
# Quest Internal Menu
# ============================================================

@router.callback_query(lambda callback: callback.data == "quest:menu")
async def quest_internal_menu(callback: CallbackQuery):
    await callback.answer()

    text = (
        "📜 <b>مأموریت‌ها</b>\n\n"
        "دسته‌بندی موردنظر خود را انتخاب کن:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=quest_main_keyboard(),
    )


# ============================================================
# Quest Category List
# ============================================================

@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("quest:list:")
    )
)
async def quest_list(callback: CallbackQuery):
    await callback.answer()

    category = callback.data.split(":", 2)[2]

    if category not in QUEST_CATEGORIES:
        await callback.message.edit_text(
            "❌ دسته‌بندی مأموریت نامعتبر است.",
            reply_markup=quest_main_keyboard(),
        )
        return

    telegram_id = callback.from_user.id

    await ensure_character_quests(
        telegram_id,
        category,
    )

    quests = await get_character_quests(
        telegram_id,
        category=category,
    )

    category_name = QUEST_CATEGORIES[category]

    if not quests:
        await callback.message.edit_text(
            f"{category_name}\n\n"
            "📭 در حال حاضر مأموریتی در این بخش وجود ندارد.",
            reply_markup=quest_main_keyboard(),
        )
        return

    text = (
        f"{category_name}\n\n"
        "📜 مأموریت‌های موجود:\n"
        "برای مشاهده جزئیات، یک مأموریت را انتخاب کن."
    )

    await callback.message.edit_text(
        text,
        reply_markup=quest_list_keyboard(
            quests,
            category,
        ),
    )


# ============================================================
# Current Quests
# ============================================================

@router.callback_query(
    lambda callback: callback.data == "quest:current_list"
)
async def current_quests(callback: CallbackQuery):
    await callback.answer()

    telegram_id = callback.from_user.id

    all_quests = []

    for category in (
        "story",
        "daily",
        "achievement",
    ):
        await ensure_character_quests(
            telegram_id,
            category,
        )

        quests = await get_character_quests(
            telegram_id,
            category=category,
        )

        all_quests.extend(quests)

    if not all_quests:
        await callback.message.edit_text(
            "📌 <b>مأموریت‌های من</b>\n\n"
            "📭 هنوز مأموریتی برای تو فعال نشده است.",
            reply_markup=quest_current_list_keyboard(),
        )
        return

    active = []
    completed = []
    claimed = []

    for character_quest, quest in all_quests:
        if character_quest.status == "active":
            active.append((character_quest, quest))

        elif character_quest.status == "completed":
            completed.append((character_quest, quest))

        elif character_quest.status == "claimed":
            claimed.append((character_quest, quest))

    lines = [
        "📌 <b>مأموریت‌های من</b>",
        "",
    ]

    if active:
        lines.append("🟡 <b>فعال</b>")
        for character_quest, quest in active:
            lines.append(
                f"• {quest.name} "
                f"— {character_quest.progress}/{quest.required_amount}"
            )
        lines.append("")

    if completed:
        lines.append("✅ <b>تکمیل‌شده و آماده دریافت</b>")
        for character_quest, quest in completed:
            lines.append(
                f"• {quest.name} 🎁"
            )
        lines.append("")

    if claimed:
        lines.append("🎁 <b>دریافت‌شده</b>")
        for character_quest, quest in claimed:
            lines.append(
                f"• {quest.name}"
            )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=quest_current_list_keyboard(),
    )


# ============================================================
# Quest Detail
# ============================================================

@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("quest:view:")
    )
)
async def quest_detail(callback: CallbackQuery):
    await callback.answer()

    try:
        quest_id = int(
            callback.data.split(":", 2)[2]
        )
    except (ValueError, IndexError):
        await callback.message.edit_text(
            "❌ شناسه مأموریت نامعتبر است.",
            reply_markup=quest_main_keyboard(),
        )
        return

    telegram_id = callback.from_user.id

    quest = await get_quest(quest_id)

    if quest is None or not quest.is_active:
        await callback.message.edit_text(
            "❌ این مأموریت دیگر فعال نیست.",
            reply_markup=quest_main_keyboard(),
        )
        return

    character_quest = await get_character_quest(
        telegram_id,
        quest_id,
    )

    if character_quest is None:
        await callback.message.edit_text(
            "❌ این مأموریت برای قهرمان تو فعال نشده است.",
            reply_markup=quest_main_keyboard(),
        )
        return

    status = format_quest_status(
        character_quest.status
    )

    objective = format_objective_type(
        quest.objective_type
    )

    progress = format_quest_progress(
        character_quest.progress,
        quest.required_amount,
    )

    can_claim = (
        character_quest.status == "completed"
        and character_quest.progress >= quest.required_amount
    )

    text = (
        f"📜 <b>{quest.name}</b>\n\n"
        f"📝 {quest.description}\n\n"
        f"🏷️ دسته‌بندی: "
        f"{QUEST_CATEGORIES.get(quest.category, quest.category)}\n"
        f"🎯 هدف: {objective}\n"
        f"📊 پیشرفت:\n{progress}\n\n"
        f"📌 وضعیت: {status}\n\n"
        f"🎁 <b>پاداش</b>\n"
        f"{format_reward(quest)}"
    )

    if quest.min_level > 1:
        text += (
            f"\n\n🔒 حداقل سطح: {quest.min_level}"
        )

    if quest.is_repeatable:
        text += "\n🔄 این مأموریت روزانه است."

    await callback.message.edit_text(
        text,
        reply_markup=quest_detail_keyboard(
            quest.id,
            can_claim,
        ),
    )


# ============================================================
# Claim Quest Reward
# ============================================================

@router.callback_query(
    lambda callback: (
        callback.data is not None
        and callback.data.startswith("quest:claim:")
    )
)
async def claim_quest_reward(callback: CallbackQuery):
    try:
        quest_id = int(
            callback.data.split(":", 2)[2]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "❌ شناسه مأموریت نامعتبر است.",
            show_alert=True,
        )
        return

    telegram_id = callback.from_user.id

    success, message = await claim_quest(
        telegram_id,
        quest_id,
    )

    if not success:
        await callback.answer(
            message,
            show_alert=True,
        )
        return

    await callback.answer(
        "🎁 پاداش دریافت شد!",
        show_alert=True,
    )

    quest = await get_quest(quest_id)

    if quest is None:
        await callback.message.edit_text(
            message,
            reply_markup=quest_main_keyboard(),
        )
        return

    character_quest = await get_character_quest(
        telegram_id,
        quest_id,
    )

    if character_quest is None:
        await callback.message.edit_text(
            message,
            reply_markup=quest_main_keyboard(),
        )
        return

    text = (
        f"🎉 <b>مأموریت تکمیل شد!</b>\n\n"
        f"📜 {quest.name}\n\n"
        f"{message}\n\n"
        f"📌 وضعیت: "
        f"{format_quest_status(character_quest.status)}"
    )

    if quest.is_repeatable:
        text += (
            "\n\n📅 این مأموریت دوباره از روز بعد "
            "قابل انجام خواهد بود."
        )

    await callback.message.edit_text(
        text,
        reply_markup=quest_detail_keyboard(
            quest.id,
            False,
        ),
    )