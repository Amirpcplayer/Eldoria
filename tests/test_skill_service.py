import time

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from database.database import AsyncSessionLocal
from models.character import Character
from models.character_skill import CharacterSkill
from models.skill import Skill

from services.skill_service import (
    can_learn_skill,
    get_character_skill,
    get_character_skills,
    get_next_available_slot,
    get_skill_upgrade_info,
    get_used_skill_slots,
    unlock_skill,
    upgrade_skill,
)


TEST_TELEGRAM_ID = (
    2_000_000_000 + int(time.time() * 1000) % 100_000_000
)
TEST_NAME = f"SkillTest_{int(time.time() * 1000)}"


async def cleanup_test_data():
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == TEST_TELEGRAM_ID
            )
        )

        if character is not None:
            await session.execute(
                delete(CharacterSkill).where(
                    CharacterSkill.character_id == character.id
                )
            )

            await session.delete(character)
            await session.commit()


async def create_test_character():
    async with AsyncSessionLocal() as session:
        character = Character(
            telegram_id=TEST_TELEGRAM_ID,
            name=TEST_NAME,
            race="Human",
            level=1,
            xp=0,
            skill_xp=5000,
            gold=10000,
            gems=0,
            hp=100,
            max_hp=100,
            mana=100,
            max_mana=100,
            attack=10,
            magic_power=10,
            defense=8,
            magic_defense=8,
            speed=10,
            accuracy=10,
            luck=5,
            critical=5,
        )

        session.add(character)
        await session.commit()
        await session.refresh(character)

        return character


async def get_test_skill():
    async with AsyncSessionLocal() as session:
        skill = await session.scalar(
            select(Skill)
            .where(Skill.is_active.is_(True))
            .order_by(Skill.id)
        )

        assert skill is not None, "No active skill exists in database."

        return skill


@pytest_asyncio.fixture(autouse=True)
async def clean_before_after():
    await cleanup_test_data()

    yield

    await cleanup_test_data()


@pytest.mark.asyncio
async def test_initial_state():
    character = await create_test_character()

    assert await get_character_skills(character.id) == []
    assert await get_used_skill_slots(character.id) == 0

    assert await get_next_available_slot(
        character.id,
        character.level,
    ) == 1


@pytest.mark.asyncio
async def test_can_learn_and_unlock_skill():
    character = await create_test_character()
    skill = await get_test_skill()

    can_learn, message = await can_learn_skill(
        character.id,
        skill.id,
    )

    assert can_learn is True
    assert message == "OK"

    success, message = await unlock_skill(
        character.telegram_id,
        skill.id,
    )

    assert success is True
    assert "موفقیت" in message

    character_skill = await get_character_skill(
        character.id,
        skill.id,
    )

    assert character_skill is not None
    assert character_skill.unlocked is True
    assert character_skill.level == 1
    assert character_skill.slot == 1

    assert await get_used_skill_slots(character.id) == 1


@pytest.mark.asyncio
async def test_upgrade_skill():
    character = await create_test_character()
    skill = await get_test_skill()

    success, _ = await unlock_skill(
        character.telegram_id,
        skill.id,
    )

    assert success is True

    success, message, info = await get_skill_upgrade_info(
        character.telegram_id,
        skill.id,
    )

    assert success is True
    assert message == "OK"
    assert info is not None
    assert info["current_level"] == 1
    assert info["next_level"] == 2
    assert info["xp_cost"] == 500
    assert info["gold_cost"] == 1000
    assert info["can_upgrade"] is True

    success, _ = await upgrade_skill(
        character.telegram_id,
        skill.id,
    )

    assert success is True

    async with AsyncSessionLocal() as session:
        updated_character = await session.scalar(
            select(Character).where(
                Character.telegram_id == TEST_TELEGRAM_ID
            )
        )

        updated_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.skill_id == skill.id,
            )
        )

        assert updated_character is not None
        assert updated_skill is not None

        assert updated_character.skill_xp == 4500
        assert updated_character.gold == 9000
        assert updated_skill.level == 2


@pytest.mark.asyncio
async def test_duplicate_unlock_rejected():
    character = await create_test_character()
    skill = await get_test_skill()

    success, _ = await unlock_skill(
        character.telegram_id,
        skill.id,
    )

    assert success is True

    success, message = await unlock_skill(
        character.telegram_id,
        skill.id,
    )

    assert success is False
    assert "قبلاً" in message


@pytest.mark.asyncio
async def test_upgrade_without_learning_rejected():
    character = await create_test_character()
    skill = await get_test_skill()

    success, message, info = await get_skill_upgrade_info(
        character.telegram_id,
        skill.id,
    )

    assert success is False
    assert info is None
    assert "یاد نگرفته" in message

    success, message = await upgrade_skill(
        character.telegram_id,
        skill.id,
    )

    assert success is False
    assert "یاد نگرفته" in message