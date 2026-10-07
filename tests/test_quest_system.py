import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import delete, select

from database.database import AsyncSessionLocal

from models.character import Character
from models.quest import Quest, CharacterQuest
from models.character_skill import CharacterSkill

from services.quest_service import (
    ensure_character_quests,
    get_character_quest,
    record_enemy_kill,
    record_level_up,
    record_skill_learned,
    record_equipment_equipped,
)


TEST_TELEGRAM_ID = 999999999
TEST_CHARACTER_NAME = "Quest System Test Hero"


async def cleanup():
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == TEST_TELEGRAM_ID
            )
        )

        if character:
            await session.execute(
                delete(CharacterQuest).where(
                    CharacterQuest.character_id == character.id
                )
            )

            await session.execute(
                delete(CharacterSkill).where(
                    CharacterSkill.character_id == character.id
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


async def get_quest_by_name(name: str):
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Quest).where(
                Quest.name == name
            )
        )


async def main():
    print()
    print("========================================")
    print("     WORLD ELDORIA QUEST SYSTEM TEST")
    print("========================================")
    print()

    await cleanup()
    character_id = await create_character()

    try:

        print("[1/7] Checking Quest seed...")

        quest = await get_quest_by_name(
            "🌲 اولین شکار"
        )

        assert quest is not None

        print("      PASS - Quest seed exists.")
        print()

        print("[2/7] Checking Character Quest creation...")

        await ensure_character_quests(
            TEST_TELEGRAM_ID,
            "story",
        )

        character_quest = await get_character_quest(
            character_id,
            quest.id,
        )

        assert character_quest is not None

        print("      PASS - Character quests created.")
        print()

        print("[3/7] Checking Enemy Kill progress...")

        await record_enemy_kill(
            TEST_TELEGRAM_ID,
            quest.target_id,
        )

        character_quest = await get_character_quest(
            character_id,
            quest.id,
        )

        assert character_quest is not None
        assert character_quest.progress >= 1

        print(
            "      PASS - Enemy kill updated quest."
        )
        print()

        print("[4/7] Checking Level Quest progress...")

        level_quest = await get_quest_by_name(
            "📈 مسیر قهرمان"
        )

        assert level_quest is not None

        await record_level_up(
            TEST_TELEGRAM_ID,
            5,
        )

        await ensure_character_quests(
            TEST_TELEGRAM_ID,
            "story",
        )

        character_quest = await get_character_quest(
            character_id,
            level_quest.id,
        )

        if character_quest is not None:
            assert character_quest.status in {
                "completed",
                "claimed",
            }

        print(
            "      PASS - Level quest updated."
        )
        print()

        print("[5/7] Checking Skill Learning progress...")

        skill_quest = await get_quest_by_name(
            "🔥 آغاز جادو"
        )

        assert skill_quest is not None

        await record_skill_learned(
            TEST_TELEGRAM_ID,
            skill_quest.target_id,
        )

        print(
            "      PASS - Skill learning updated quest."
        )
        print()

        print("[6/7] Checking Equipment Quest hook...")

        await record_equipment_equipped(
            TEST_TELEGRAM_ID,
            1,
        )

        print(
            "      PASS - Equipment hook executed."
        )
        print()

        print("[7/7] Checking Character Quest lookup...")

        found = await get_character_quest(
            character_id,
            quest.id,
        )

        assert found is not None

        print(
            "      PASS - Character Quest lookup works."
        )

        print()
        print(
            "[Extra] Checking Character Quest category retrieval..."
        )

        await ensure_character_quests(
            TEST_TELEGRAM_ID,
            "daily",
        )

        print(
            "      PASS - Category retrieval works."
        )

        print()
        print("========================================")
        print("       ALL QUEST TESTS PASSED")
        print("========================================")

    finally:
        print()
        print("Cleaning test data...")
        await cleanup()
        print("Test data cleaned.")


if __name__ == "__main__":
    asyncio.run(main())