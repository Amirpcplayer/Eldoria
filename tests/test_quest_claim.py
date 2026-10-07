import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import delete, select

from database.database import AsyncSessionLocal

from models.character import Character
from models.quest import Quest, CharacterQuest
from models.equipment import Equipment, CharacterEquipment

from services.quest_service import (
    claim_quest,
    ensure_character_quests,
    get_character_quest,
)


TEST_TELEGRAM_ID = 999999998
TEST_CHARACTER_NAME = "Quest Claim Test Hero"


async def cleanup():
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == TEST_TELEGRAM_ID
            )
        )

        if character:
            await session.execute(
                delete(CharacterEquipment).where(
                    CharacterEquipment.character_id == character.id
                )
            )

            await session.execute(
                delete(CharacterQuest).where(
                    CharacterQuest.character_id == character.id
                )
            )

            await session.delete(character)

        await session.commit()


async def create_character():
    async with AsyncSessionLocal() as session:
        character = Character(
            telegram_id=TEST_TELEGRAM_ID,
            name=TEST_CHARACTER_NAME,
            race="human",
            level=1,
            xp=0,
            skill_xp=0,
            gold=100,
            gems=0,
        )

        session.add(character)

        await session.commit()
        await session.refresh(character)

        return character.id


async def get_character():
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == TEST_TELEGRAM_ID
            )
        )


async def get_quest(name: str):
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Quest).where(
                Quest.name == name
            )
        )


async def complete_quest(quest_id: int):
    character = await get_character()

    assert character is not None

    async with AsyncSessionLocal() as session:
        character_quest = await session.scalar(
            select(CharacterQuest).where(
                CharacterQuest.character_id == character.id,
                CharacterQuest.quest_id == quest_id,
            )
        )

        assert character_quest is not None

        quest = await session.scalar(
            select(Quest).where(
                Quest.id == quest_id
            )
        )

        assert quest is not None

        character_quest.progress = quest.required_amount
        character_quest.status = "completed"
        character_quest.completed_at = datetime.utcnow()
        character_quest.claimed_at = None

        await session.commit()


async def test_basic_claim():
    print("[1/8] Checking basic Quest claim...")

    quest = await get_quest("🌲 اولین شکار")

    assert quest is not None

    await ensure_character_quests(
        TEST_TELEGRAM_ID,
        "story",
    )

    await complete_quest(quest.id)

    success, _ = await claim_quest(
        TEST_TELEGRAM_ID,
        quest.id,
    )

    assert success is True

    print("      PASS - Basic Quest claim works.")


async def test_xp_reward():
    print("[2/8] Checking Character XP reward...")

    quest = await get_quest("🌲 اولین شکار")

    assert quest is not None
    assert quest.reward_xp > 0

    print(
        f"      PASS - Quest XP reward configured: "
        f"{quest.reward_xp}"
    )


async def test_skill_xp_gold():
    print("[3/8] Checking Skill XP and Gold reward...")

    quest = await get_quest("🌲 اولین شکار")

    assert quest is not None
    assert quest.reward_skill_xp > 0
    assert quest.reward_gold > 0

    print(
        "      PASS - Skill XP and Gold fields are valid."
    )


async def test_duplicate_claim():
    print("[4/8] Checking duplicate claim protection...")

    quest = await get_quest("🌲 اولین شکار")

    assert quest is not None

    success, _ = await claim_quest(
        TEST_TELEGRAM_ID,
        quest.id,
    )

    assert success is False

    print("      PASS - Duplicate claim blocked.")


async def test_incomplete_claim():
    print("[5/8] Checking incomplete Quest protection...")

    quest = await get_quest("🌲 اولین شکار")

    assert quest is not None

    await ensure_character_quests(
        TEST_TELEGRAM_ID,
        "story",
    )

    character = await get_character()

    assert character is not None

    async with AsyncSessionLocal() as session:
        character_quest = await session.scalar(
            select(CharacterQuest).where(
                CharacterQuest.character_id == character.id,
                CharacterQuest.quest_id == quest.id,
            )
        )

        assert character_quest is not None

        character_quest.status = "active"
        character_quest.progress = 0
        character_quest.completed_at = None
        character_quest.claimed_at = None

        await session.commit()

    success, _ = await claim_quest(
        TEST_TELEGRAM_ID,
        quest.id,
    )

    assert success is False

    print(
        "      PASS - Incomplete Quest claim blocked."
    )


async def test_level_up():
    print("[6/8] Checking Level Up from Quest reward...")

    quest = await get_quest("🌲 اولین شکار")

    assert quest is not None

    character = await get_character()

    assert character is not None

    async with AsyncSessionLocal() as session:
        db_character = await session.scalar(
            select(Character).where(
                Character.id == character.id
            )
        )

        assert db_character is not None

        db_character.level = 1
        db_character.xp = 900
        db_character.skill_xp = 0
        db_character.gold = 100

        character_quest = await session.scalar(
            select(CharacterQuest).where(
                CharacterQuest.character_id == character.id,
                CharacterQuest.quest_id == quest.id,
            )
        )

        assert character_quest is not None

        character_quest.status = "completed"
        character_quest.progress = quest.required_amount
        character_quest.completed_at = datetime.utcnow()
        character_quest.claimed_at = None

        await session.commit()

    success, _ = await claim_quest(
        TEST_TELEGRAM_ID,
        quest.id,
    )

    assert success is True

    character = await get_character()

    assert character is not None
    assert character.level >= 2

    print(
        "      PASS - Quest reward triggered Level Up."
    )


async def test_equipment_reward():
    print("[7/8] Checking Equipment reward...")

    quest = await get_quest("🌲 اولین شکار")

    assert quest is not None

    character = await get_character()

    assert character is not None

    async with AsyncSessionLocal() as session:

        equipment = await session.scalar(
            select(Equipment).where(
                Equipment.is_active.is_(True)
            )
        )

        assert equipment is not None

        db_quest = await session.scalar(
            select(Quest).where(
                Quest.id == quest.id
            )
        )

        assert db_quest is not None

        old_reward = db_quest.reward_equipment_id

        db_quest.reward_equipment_id = equipment.id

        character_quest = await session.scalar(
            select(CharacterQuest).where(
                CharacterQuest.character_id == character.id,
                CharacterQuest.quest_id == quest.id,
            )
        )

        assert character_quest is not None

        character_quest.status = "completed"
        character_quest.progress = quest.required_amount
        character_quest.completed_at = datetime.utcnow()
        character_quest.claimed_at = None

        await session.commit()

        equipment_id = equipment.id

    try:
        success, _ = await claim_quest(
            TEST_TELEGRAM_ID,
            quest.id,
        )

        assert success is True

        async with AsyncSessionLocal() as session:
            reward = await session.scalar(
                select(CharacterEquipment).where(
                    CharacterEquipment.character_id == character.id,
                    CharacterEquipment.equipment_id == equipment_id,
                )
            )

            assert reward is not None
            assert reward.quantity >= 1

    finally:
        async with AsyncSessionLocal() as session:
            db_quest = await session.scalar(
                select(Quest).where(
                    Quest.id == quest.id
                )
            )

            if db_quest:
                db_quest.reward_equipment_id = old_reward
                await session.commit()

    print("      PASS - Equipment reward works.")


async def test_repeatable():
    print("[8/8] Checking Repeatable Quest...")

    quest = await get_quest("⚔️ شکار روزانه")

    assert quest is not None
    assert quest.is_repeatable is True

    await ensure_character_quests(
        TEST_TELEGRAM_ID,
        "daily",
    )

    character = await get_character()

    assert character is not None

    character_quest = await get_character_quest(
        character.id,
        quest.id,
    )

    assert character_quest is not None

    await complete_quest(quest.id)

    success, _ = await claim_quest(
        TEST_TELEGRAM_ID,
        quest.id,
    )

    assert success is True

    character_quest = await get_character_quest(
        character.id,
        quest.id,
    )

    assert character_quest is not None
    assert character_quest.status == "claimed"

    # همان روز نباید دوباره Claim شود
    success, _ = await claim_quest(
        TEST_TELEGRAM_ID,
        quest.id,
    )

    assert success is False

    # شبیه‌سازی روز بعد
    async with AsyncSessionLocal() as session:
        db_character_quest = await session.scalar(
            select(CharacterQuest).where(
                CharacterQuest.id == character_quest.id
            )
        )

        assert db_character_quest is not None

        db_character_quest.claimed_at = (
            datetime.utcnow() - timedelta(days=1)
        )

        await session.commit()

    await ensure_character_quests(
        TEST_TELEGRAM_ID,
        "daily",
    )

    character_quest = await get_character_quest(
        character.id,
        quest.id,
    )

    assert character_quest is not None
    assert character_quest.status == "active"
    assert character_quest.progress == 0
    assert character_quest.claimed_at is None

    print(
        "      PASS - Repeatable daily Quest works."
    )


async def main():
    print()
    print("========================================")
    print("       WORLD ELDORIA QUEST CLAIM TEST")
    print("========================================")
    print()

    await cleanup()
    await create_character()

    try:
        await test_basic_claim()
        await test_xp_reward()
        await test_skill_xp_gold()
        await test_duplicate_claim()
        await test_incomplete_claim()
        await test_level_up()
        await test_equipment_reward()
        await test_repeatable()

        print()
        print("========================================")
        print("       ALL QUEST CLAIM TESTS PASSED")
        print("========================================")

    finally:
        print()
        print("Cleaning test data...")
        await cleanup()
        print("Test data cleaned.")


if __name__ == "__main__":
    asyncio.run(main())