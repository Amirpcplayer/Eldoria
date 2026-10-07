from datetime import datetime

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.quest import Quest, CharacterQuest
from models.equipment import Equipment, CharacterEquipment


QUEST_CATEGORIES = {
    "story": "📖 داستانی",
    "daily": "📅 روزانه",
    "achievement": "🏆 دستاورد",
}

QUEST_STATUS = {
    "active": "🟡 فعال",
    "completed": "✅ تکمیل شده",
    "claimed": "🎁 دریافت شده",
}

OBJECTIVE_TYPES = {
    "kill_enemy": "⚔️ کشتن دشمن",
    "level": "📈 رسیدن به سطح",
    "learn_skill": "🔮 یادگیری مهارت",
    "equip": "🛡️ تجهیز آیتم",
}


# ============================================================
# BASIC QUERIES
# ============================================================

async def get_character(telegram_id: int):
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )


async def get_quest(quest_id: int):
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Quest).where(
                Quest.id == quest_id,
                Quest.is_active.is_(True),
            )
        )


async def get_active_quests(category: str | None = None):
    async with AsyncSessionLocal() as session:
        query = select(Quest).where(
            Quest.is_active.is_(True)
        )

        if category:
            query = query.where(
                Quest.category == category
            )

        query = query.order_by(
            Quest.min_level,
            Quest.id,
        )

        result = await session.scalars(query)

        return list(result.all())


async def get_character_quest(
    character_id: int,
    quest_id: int,
):
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(CharacterQuest).where(
                CharacterQuest.character_id == character_id,
                CharacterQuest.quest_id == quest_id,
            )
        )


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _is_same_day(
    first: datetime | None,
    second: datetime,
) -> bool:
    if first is None:
        return False

    return first.date() == second.date()


async def _reset_daily_quest_if_needed(
    session,
    character_quest: CharacterQuest,
):
    if character_quest.status != "claimed":
        return

    if character_quest.claimed_at is None:
        return

    now = datetime.utcnow()

    if character_quest.claimed_at.date() < now.date():
        character_quest.progress = 0
        character_quest.status = "active"
        character_quest.completed_at = None
        character_quest.claimed_at = None


async def _is_prerequisite_completed(
    session,
    character_id: int,
    quest: Quest,
) -> bool:
    if quest.prerequisite_quest_id is None:
        return True

    prerequisite = await session.scalar(
        select(CharacterQuest).where(
            CharacterQuest.character_id == character_id,
            CharacterQuest.quest_id == quest.prerequisite_quest_id,
        )
    )

    if prerequisite is None:
        return False

    return prerequisite.status == "claimed"


async def _can_create_character_quest(
    session,
    character: Character,
    quest: Quest,
) -> bool:
    if not quest.is_active:
        return False

    if character.level < quest.min_level:
        return False

    return await _is_prerequisite_completed(
        session,
        character.id,
        quest,
    )


# ============================================================
# CHARACTER QUEST CREATION
# ============================================================

async def ensure_character_quests(
    telegram_id: int,
    category: str | None = None,
):
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return False

        query = select(Quest).where(
            Quest.is_active.is_(True)
        )

        if category:
            query = query.where(
                Quest.category == category
            )

        quests = list(
            (await session.scalars(query)).all()
        )

        now = datetime.utcnow()

        for quest in quests:
            character_quest = await session.scalar(
                select(CharacterQuest).where(
                    CharacterQuest.character_id == character.id,
                    CharacterQuest.quest_id == quest.id,
                )
            )

            if character_quest is not None:
                await _reset_daily_quest_if_needed(
                    session,
                    character_quest,
                )

                continue

            if not await _can_create_character_quest(
                session,
                character,
                quest,
            ):
                continue

            session.add(
                CharacterQuest(
                    character_id=character.id,
                    quest_id=quest.id,
                    progress=0,
                    status="active",
                    created_at=now,
                )
            )

        await session.commit()

        return True


# ============================================================
# CHARACTER QUEST LIST
# ============================================================

async def get_character_quests(
    telegram_id: int,
    category: str | None = None,
):
    await ensure_character_quests(
        telegram_id,
        category,
    )

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return []

        query = (
            select(CharacterQuest, Quest)
            .join(
                Quest,
                Quest.id == CharacterQuest.quest_id,
            )
            .where(
                CharacterQuest.character_id == character.id,
                Quest.is_active.is_(True),
            )
        )

        if category:
            query = query.where(
                Quest.category == category
            )

        query = query.order_by(
            Quest.min_level,
            Quest.id,
        )

        result = await session.execute(query)

        return list(result.all())


# ============================================================
# QUEST PROGRESS
# ============================================================

async def update_progress(
    telegram_id: int,
    objective_type: str,
    amount: int = 1,
    target_id: int | None = None,
):
    if amount <= 0:
        return 0

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return 0

        query = (
            select(CharacterQuest, Quest)
            .join(
                Quest,
                Quest.id == CharacterQuest.quest_id,
            )
            .where(
                CharacterQuest.character_id == character.id,
                CharacterQuest.status == "active",
                Quest.is_active.is_(True),
                Quest.objective_type == objective_type,
            )
        )

        rows = list(
            (await session.execute(query)).all()
        )

        changed = 0

        for character_quest, quest in rows:

            if character.level < quest.min_level:
                continue

            if target_id is not None:
                if quest.target_id is not None:
                    if quest.target_id != target_id:
                        continue

            character_quest.progress = min(
                character_quest.progress + amount,
                quest.required_amount,
            )

            if character_quest.progress >= quest.required_amount:
                character_quest.progress = quest.required_amount
                character_quest.status = "completed"
                character_quest.completed_at = datetime.utcnow()

            changed += 1

        if changed:
            await session.commit()

        return changed


# ============================================================
# EVENT HOOKS
# ============================================================

async def record_enemy_kill(
    telegram_id: int,
    enemy_id: int,
):
    return await update_progress(
        telegram_id=telegram_id,
        objective_type="kill_enemy",
        amount=1,
        target_id=enemy_id,
    )


async def record_level_up(
    telegram_id: int,
    new_level: int,
):
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return 0

        query = (
            select(CharacterQuest, Quest)
            .join(
                Quest,
                Quest.id == CharacterQuest.quest_id,
            )
            .where(
                CharacterQuest.character_id == character.id,
                CharacterQuest.status == "active",
                Quest.is_active.is_(True),
                Quest.objective_type == "level",
            )
        )

        rows = list(
            (await session.execute(query)).all()
        )

        changed = 0

        for character_quest, quest in rows:
            target_level = quest.target_id

            if target_level is None:
                target_level = quest.required_amount

            if new_level < target_level:
                continue

            character_quest.progress = quest.required_amount
            character_quest.status = "completed"
            character_quest.completed_at = datetime.utcnow()

            changed += 1

        if changed:
            await session.commit()

        return changed


async def record_skill_learned(
    telegram_id: int,
    skill_id: int,
):
    return await update_progress(
        telegram_id=telegram_id,
        objective_type="learn_skill",
        amount=1,
        target_id=skill_id,
    )


async def record_equipment_equipped(
    telegram_id: int,
    equipment_id: int,
):
    return await update_progress(
        telegram_id=telegram_id,
        objective_type="equip",
        amount=1,
        target_id=equipment_id,
    )


# ============================================================
# REWARD / LEVEL HELPERS
# ============================================================

MAX_CHARACTER_LEVEL = 100


def _required_character_xp(level: int) -> int:
    if level >= MAX_CHARACTER_LEVEL:
        return 0

    return level * 1000


async def _apply_character_xp(
    character: Character,
    amount: int,
) -> int:
    if amount <= 0:
        return 0

    if character.level >= MAX_CHARACTER_LEVEL:
        return 0

    character.xp += amount

    levels_gained = 0

    while character.level < MAX_CHARACTER_LEVEL:
        required = _required_character_xp(
            character.level
        )

        if required <= 0:
            break

        if character.xp < required:
            break

        character.xp -= required
        character.level += 1
        levels_gained += 1

    return levels_gained


async def _update_level_quests_after_levelup(
    session,
    character: Character,
):
    query = (
        select(CharacterQuest, Quest)
        .join(
            Quest,
            Quest.id == CharacterQuest.quest_id,
        )
        .where(
            CharacterQuest.character_id == character.id,
            CharacterQuest.status == "active",
            Quest.is_active.is_(True),
            Quest.objective_type == "level",
        )
    )

    rows = list(
        (await session.execute(query)).all()
    )

    for character_quest, quest in rows:
        target_level = quest.target_id

        if target_level is None:
            target_level = quest.required_amount

        if character.level >= target_level:
            character_quest.progress = quest.required_amount
            character_quest.status = "completed"
            character_quest.completed_at = datetime.utcnow()


async def _add_equipment_reward(
    session,
    character_id: int,
    equipment_id: int,
):
    equipment = await session.scalar(
        select(Equipment).where(
            Equipment.id == equipment_id,
            Equipment.is_active.is_(True),
        )
    )

    if equipment is None:
        return False

    character_equipment = await session.scalar(
        select(CharacterEquipment).where(
            CharacterEquipment.character_id == character_id,
            CharacterEquipment.equipment_id == equipment_id,
        )
    )

    if character_equipment is None:
        character_equipment = CharacterEquipment(
            character_id=character_id,
            equipment_id=equipment_id,
            quantity=1,
            equipped=False,
        )

        session.add(character_equipment)

    else:
        character_equipment.quantity += 1

    return True


# ============================================================
# CLAIM QUEST
# ============================================================

async def claim_quest(
    telegram_id: int,
    quest_id: int,
) -> tuple[bool, str]:

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return False, "❌ قهرمان پیدا نشد."

        quest = await session.scalar(
            select(Quest).where(
                Quest.id == quest_id,
                Quest.is_active.is_(True),
            )
        )

        if quest is None:
            return False, "❌ مأموریت پیدا نشد."

        character_quest = await session.scalar(
            select(CharacterQuest).where(
                CharacterQuest.character_id == character.id,
                CharacterQuest.quest_id == quest.id,
            )
        )

        if character_quest is None:
            return False, "❌ این مأموریت برای شما فعال نیست."

        # Daily quest reset
        if quest.is_repeatable:
            await _reset_daily_quest_if_needed(
                session,
                character_quest,
            )

        # Already claimed
        if character_quest.status == "claimed":
            if quest.is_repeatable:
                return (
                    False,
                    "⏳ این مأموریت روزانه را امروز دریافت کرده‌اید.",
                )

            return (
                False,
                "❌ جایزه این مأموریت قبلاً دریافت شده است.",
            )

        # Must be completed
        if character_quest.status != "completed":
            return (
                False,
                "❌ ابتدا مأموریت را کامل کنید.",
            )

        if character_quest.progress < quest.required_amount:
            return (
                False,
                "❌ پیشرفت مأموریت کافی نیست.",
            )

        # Minimum level
        if character.level < quest.min_level:
            return (
                False,
                "❌ سطح قهرمان برای این مأموریت کافی نیست.",
            )

        # ====================================================
        # APPLY REWARDS
        # ====================================================

        old_level = character.level

        levels_gained = await _apply_character_xp(
            character,
            quest.reward_xp,
        )

        character.skill_xp += max(
            0,
            quest.reward_skill_xp,
        )

        character.gold += max(
            0,
            quest.reward_gold,
        )

        equipment_rewarded = False

        if quest.reward_equipment_id is not None:
            equipment_rewarded = await _add_equipment_reward(
                session,
                character.id,
                quest.reward_equipment_id,
            )

        character_quest.claimed_at = datetime.utcnow()

        if quest.is_repeatable:
            # Daily quests remain claimed until the next day.
            character_quest.status = "claimed"
            character_quest.progress = quest.required_amount

        else:
            character_quest.status = "claimed"

        # Update level-based quests caused by reward XP
        if levels_gained > 0:
            await _update_level_quests_after_levelup(
                session,
                character,
            )

        await session.commit()

        reward_lines = []

        if quest.reward_xp > 0:
            reward_lines.append(
                f"✨ {quest.reward_xp:,} XP"
            )

        if quest.reward_skill_xp > 0:
            reward_lines.append(
                f"🔮 {quest.reward_skill_xp:,} Skill XP"
            )

        if quest.reward_gold > 0:
            reward_lines.append(
                f"💰 {quest.reward_gold:,} Gold"
            )

        if equipment_rewarded:
            reward_lines.append(
                "🎁 تجهیزات"
            )

        message = (
            "🎉 <b>مأموریت کامل شد!</b>\n\n"
            f"📜 {quest.name}\n\n"
        )

        if reward_lines:
            message += (
                "🎁 <b>جوایز:</b>\n"
                + "\n".join(reward_lines)
                + "\n"
            )

        if levels_gained > 0:
            message += (
                f"\n📈 سطح شما از "
                f"{old_level} به "
                f"{character.level} رسید!"
            )

        if quest.is_repeatable:
            message += (
                "\n\n📅 این مأموریت فردا دوباره "
                "قابل انجام خواهد بود."
            )

        return True, message