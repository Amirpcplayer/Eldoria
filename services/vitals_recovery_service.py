"""Elapsed-time HP/Mana regeneration; no background polling required."""
from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character

REGEN_INTERVAL_SECONDS = 60 * 60
REGEN_FRACTION_PER_HOUR = 0.20


async def recover_character_vitals(telegram_id: int) -> dict | None:
    """Apply 20% max HP and Mana per elapsed hour, while alive.

    Death takes priority: dead characters do not regenerate and the recovery
    clock is reset so time spent dead cannot be banked.
    """
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == int(telegram_id))
            .with_for_update()
        )
        if character is None:
            return None

        now = datetime.utcnow()
        if character.dead_until is not None:
            character.last_vitals_recovery_at = now
            await session.commit()
            return {
                "hp": int(character.hp or 0),
                "max_hp": int(character.max_hp or 100),
                "mana": int(character.mana or 0),
                "max_mana": int(character.max_mana or 100),
                "recovered_hours": 0,
                "dead": True,
            }

        last = character.last_vitals_recovery_at or character.created_at or now
        elapsed = max(0, int((now - last).total_seconds()))
        hours = elapsed // REGEN_INTERVAL_SECONDS
        if hours:
            hp_gain = max(1, int(max(1, int(character.max_hp or 100)) * REGEN_FRACTION_PER_HOUR)) * hours
            mana_gain = max(1, int(max(1, int(character.max_mana or 100)) * REGEN_FRACTION_PER_HOUR)) * hours
            character.hp = min(int(character.max_hp or 100), max(0, int(character.hp or 0)) + hp_gain)
            character.mana = min(int(character.max_mana or 100), max(0, int(character.mana or 0)) + mana_gain)
            character.last_vitals_recovery_at = last + timedelta(seconds=hours * REGEN_INTERVAL_SECONDS)
            await session.commit()
        elif character.last_vitals_recovery_at is None:
            character.last_vitals_recovery_at = now
            await session.commit()

        return {
            "hp": int(character.hp or 0),
            "max_hp": int(character.max_hp or 100),
            "mana": int(character.mana or 0),
            "max_mana": int(character.max_mana or 100),
            "recovered_hours": int(hours),
            "dead": False,
        }
