from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from sqlalchemy import select
from database.database import AsyncSessionLocal
from models.character import Character
from services.vitals_recovery_service import recover_character_vitals

logger = logging.getLogger(__name__)
REVIVE_AFTER = timedelta(minutes=10)

async def ensure_character_alive(telegram_id: int) -> tuple[bool, str]:
    """Persisted shared death/revival guard used by every combat entry point."""
    await recover_character_vitals(telegram_id)
    async with AsyncSessionLocal() as session:
        char = await session.scalar(select(Character).where(Character.telegram_id == telegram_id).with_for_update())
        if char is None:
            return False, "قهرمان پیدا نشد؛ ابتدا /start را بزن."
        now = datetime.utcnow()
        if char.dead_until and now < char.dead_until:
            remaining = max(1, int((char.dead_until - now).total_seconds()))
            return False, f"💀 قهرمانت از پا افتاده است؛ احیای خودکار تا {remaining // 60} دقیقه و {remaining % 60} ثانیهٔ دیگر انجام می‌شود."
        if char.dead_until and now >= char.dead_until:
            char.dead_until = None
            char.hp = max(1, int(char.max_hp or 100) // 2)
            char.mana = max(1, int(char.max_mana or 100) // 2)
            char.last_vitals_recovery_at = now
            await session.commit()
            return True, "✨ قهرمان احیا شد و با ۵۰٪ HP و ۵۰٪ Mana به میدان بازگشت."
        if int(char.hp or 0) <= 0:
            char.dead_until = now + REVIVE_AFTER
            await session.commit()
            return False, "💀 قهرمانت از پا افتاده است؛ احیای خودکار ۱۰ دقیقه دیگر انجام می‌شود."
        return True, ""

async def death_revival_scheduler(bot: Bot) -> None:
    """Automatically restore characters whose persistent 10-minute timer expired."""
    while True:
        try:
            now = datetime.utcnow()
            async with AsyncSessionLocal() as session:
                rows = list((await session.scalars(select(Character).where(Character.dead_until.is_not(None), Character.dead_until <= now).with_for_update().limit(200))).all())
                notices = []
                for char in rows:
                    char.hp = max(1, int(char.max_hp or 100) // 2)
                    char.mana = max(1, int(char.max_mana or 100) // 2)
                    char.last_vitals_recovery_at = now
                    char.dead_until = None
                    notices.append((int(char.telegram_id), str(char.name or "قهرمان"), int(char.hp), int(char.mana)))
                if rows:
                    await session.commit()
            for telegram_id, name, hp, mana in notices:
                try:
                    from services.combat_service import sync_character_vitals_to_battles
                    from services.pvp_service import sync_character_vitals_to_pvp
                    await sync_character_vitals_to_battles(telegram_id, hp, mana)
                    await sync_character_vitals_to_pvp(telegram_id, hp, mana)
                except Exception:
                    logger.exception("Could not sync revived HP/Mana to active battle caches")
                try:
                    await bot.send_message(telegram_id, f"✨ قهرمان {name} احیا شد!\n❤️ HP: {hp:,}\n🔷 Mana: {mana:,}\nمی‌توانی دوباره به مبارزه برگردی.")
                except Exception:
                    logger.info("Revival DM unavailable for telegram_id=%s", telegram_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Death revival scheduler failed")
        await asyncio.sleep(15)
