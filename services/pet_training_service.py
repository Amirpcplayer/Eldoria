from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select, update

from database.database import AsyncSessionLocal
from database.redis import redis
from models.character import Character
from models.social_systems import CharacterPet, Pet
from models.world_systems import CharacterActivity

logger = logging.getLogger(__name__)
TRAINING_DURATION = timedelta(hours=1)
TRAINING_XP = 100
TRAINING_BATCH_SIZE = 200


async def process_completed_pet_training(bot: Bot) -> None:
    now = datetime.utcnow()

    # Process a bounded, ordered batch. SKIP LOCKED lets multiple bot workers
    # split work without awarding training XP to the same pet twice.
    async with AsyncSessionLocal() as session:
        due = list(
            (
                await session.execute(
                    select(CharacterPet, Character, Pet)
                    .join(Character, Character.id == CharacterPet.character_id)
                    .join(Pet, Pet.id == CharacterPet.pet_id)
                    .where(
                        CharacterPet.last_training_at.is_not(None),
                        CharacterPet.training_completed_at.is_(None),
                        CharacterPet.last_training_at <= now - TRAINING_DURATION,
                    )
                    .order_by(CharacterPet.last_training_at, CharacterPet.id)
                    .limit(TRAINING_BATCH_SIZE)
                    .with_for_update(skip_locked=True, of=CharacterPet)
                )
            ).all()
        )

        for row, character, pet in due:
            level = max(1, int(row.level or 1))
            row.training_start_level = (
                level if row.training_start_level is None else row.training_start_level
            )
            row.xp = int(row.xp or 0) + TRAINING_XP

            while level < 100 and row.xp >= level * 100:
                row.xp -= level * 100
                level += 1

            row.level = level
            if level >= 5:
                row.evolution_stage = max(int(row.evolution_stage or 0), 1)
            if level >= 10:
                row.evolution_stage = max(int(row.evolution_stage or 0), 2)

            row.training_completed_at = now
            session.add(
                CharacterActivity(
                    character_id=character.id,
                    event_type="pet_training_completed",
                    details=f"pet={pet.id};xp={TRAINING_XP};level={level}",
                )
            )
        await session.commit()

    # Read only a bounded, oldest-first batch of notifications. The notification
    # timestamp is written only after Telegram accepts the DM, so a process crash
    # before sending does not permanently mark the notification as delivered.
    async with AsyncSessionLocal() as session:
        pending_ids = list(
            (
                await session.scalars(
                    select(CharacterPet.id)
                    .where(
                        CharacterPet.training_completed_at.is_not(None),
                        CharacterPet.training_notified_at.is_(None),
                    )
                    .order_by(
                        CharacterPet.training_completed_at,
                        CharacterPet.id,
                    )
                    .limit(TRAINING_BATCH_SIZE)
                )
            ).all()
        )

    for pet_row_id in pending_ids:
        lock_key = f"eldoria:pet_training_notify:{int(pet_row_id)}"
        lock_token = str(uuid.uuid4())
        try:
            acquired = await redis.set(lock_key, lock_token, nx=True, ex=120)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Could not acquire pet-training notification lock for row %s",
                pet_row_id,
            )
            continue

        if not acquired:
            continue

        try:
            # Copy only the fields needed for the Telegram message, then close
            # the DB session before network I/O so a slow Telegram response
            # cannot hold a connection or row lock.
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(CharacterPet, Character.telegram_id, Pet.name)
                    .join(Character, Character.id == CharacterPet.character_id)
                    .join(Pet, Pet.id == CharacterPet.pet_id)
                    .where(
                        CharacterPet.id == pet_row_id,
                        CharacterPet.training_completed_at.is_not(None),
                        CharacterPet.training_notified_at.is_(None),
                    )
                )
                row_data = result.first()
                if row_data is None:
                    continue

                row, telegram_id, pet_name = row_data
                level = max(1, int(row.level or 1))
                start_level = max(1, int(row.training_start_level or level))

            level_note = (
                f"\\n🎉 پت لول‌آپ کرد: Lv.{start_level} → Lv.{level}"
                if level > start_level
                else ""
            )
            message = (
                f"🐾 آموزش پت «{pet_name}» به پایان رسید!\\n"
                f"✨ XP دریافت‌شده: +{TRAINING_XP}\\n"
                f"⭐ سطح فعلی پت: Lv.{level}{level_note}"
            )

            try:
                await bot.send_message(int(telegram_id), message)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Could not send pet training result to telegram_id=%s",
                    telegram_id,
                )
                continue

            # Record delivery in a fresh short transaction after Telegram I/O.
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    update(CharacterPet)
                    .where(
                        CharacterPet.id == pet_row_id,
                        CharacterPet.training_completed_at.is_not(None),
                        CharacterPet.training_notified_at.is_(None),
                    )
                    .values(training_notified_at=datetime.utcnow())
                )
                await session.commit()
                if result.rowcount == 0:
                    logger.warning(
                        "Pet-training notification was sent but its delivery marker was not updated; row=%s",
                        pet_row_id,
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Pet-training notification processing failed for row %s",
                pet_row_id,
            )
        finally:
            # Compare-and-delete avoids deleting a lock acquired by a later worker.
            try:
                await redis.eval(
                    """
                    if redis.call('get', KEYS[1]) == ARGV[1] then
                        return redis.call('del', KEYS[1])
                    end
                    return 0
                    """,
                    1,
                    lock_key,
                    lock_token,
                )
            except Exception:
                logger.exception(
                    "Could not release pet-training notification lock for row %s",
                    pet_row_id,
                )


async def pet_training_scheduler(bot: Bot) -> None:
    while True:
        try:
            await process_completed_pet_training(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Pet training scheduler failed")
        await asyncio.sleep(30)
