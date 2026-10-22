from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.social_systems import CharacterPet, Pet
from models.world_systems import CharacterActivity

logger = logging.getLogger(__name__)
TRAINING_DURATION = timedelta(hours=1)
TRAINING_XP = 100

async def process_completed_pet_training(bot: Bot) -> None:
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        due = list((await session.execute(select(CharacterPet, Character, Pet).join(Character, Character.id == CharacterPet.character_id).join(Pet, Pet.id == CharacterPet.pet_id).where(CharacterPet.last_training_at.is_not(None), CharacterPet.training_completed_at.is_(None), CharacterPet.last_training_at <= now - TRAINING_DURATION).limit(200).with_for_update(skip_locked=True))).all())
        for row, character, pet in due:
            row.training_start_level = int(row.level or 1) if row.training_start_level is None else row.training_start_level
            row.xp += TRAINING_XP
            old_level = int(row.level or 1)
            while row.level < 100 and row.xp >= int(row.level) * 100:
                row.xp -= int(row.level) * 100
                row.level += 1
            if row.level >= 5: row.evolution_stage = max(int(row.evolution_stage or 0), 1)
            if row.level >= 10: row.evolution_stage = max(int(row.evolution_stage or 0), 2)
            row.training_completed_at = now
            session.add(CharacterActivity(character_id=character.id, event_type="pet_training_completed", details=f"pet={pet.id};xp={TRAINING_XP};level={row.level}"))
        await session.commit()
    # Completed rewards are persisted before DM delivery. If Telegram is unavailable, notification stays pending.
    async with AsyncSessionLocal() as session:
        pending = list((await session.execute(select(CharacterPet, Character, Pet).join(Character, Character.id == CharacterPet.character_id).join(Pet, Pet.id == CharacterPet.pet_id).where(CharacterPet.training_completed_at.is_not(None), CharacterPet.training_notified_at.is_(None)).limit(200))).all())
    for row, character, pet in pending:
        old_level = None
        async with AsyncSessionLocal() as session:
            # Mark as being delivered under row lock to prevent duplicate concurrent workers.
            locked = await session.scalar(select(CharacterPet).where(CharacterPet.id == row.id).with_for_update())
            if not locked or locked.training_notified_at is not None:
                continue
            # Use an interim timestamp; if send fails, clear it to allow retry.
            locked.training_notified_at = datetime.utcnow()
            await session.commit()
        level = int(row.level or 1)
        start_level = int(row.training_start_level or level)
        level_note = f"\n🎉 پت لول‌آپ کرد: Lv.{start_level} → Lv.{level}" if level > start_level else ""
        message = f"🐾 آموزش پت «{pet.name}» به پایان رسید!\n✨ XP دریافت‌شده: +{TRAINING_XP}\n⭐ سطح فعلی پت: Lv.{level}{level_note}"
        try:
            await bot.send_message(character.telegram_id, message)
        except Exception:
            logger.exception("Could not send pet training result to telegram_id=%s", character.telegram_id)
            async with AsyncSessionLocal() as session:
                locked = await session.scalar(select(CharacterPet).where(CharacterPet.id == row.id).with_for_update())
                if locked and locked.training_notified_at is not None:
                    locked.training_notified_at = None
                    await session.commit()

async def pet_training_scheduler(bot: Bot) -> None:
    while True:
        try:
            await process_completed_pet_training(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Pet training scheduler failed")
        await asyncio.sleep(30)
