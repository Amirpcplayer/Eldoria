"""Seed pets and the launch event; importing this module never writes to the DB.

Run with the bot stopped: python -m utils.seed_social_systems
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.clock import utcnow_naive

from database.database import AsyncSessionLocal
from models.social_systems import GameEvent
from sqlalchemy import select
from utils.sync_pet_catalog import seed_pets


async def main():
    async with AsyncSessionLocal() as session:
        await seed_pets(session)
        now = utcnow_naive()  # Preserve the project's naive UTC convention.
        event = await session.scalar(
            select(GameEvent).where(GameEvent.name == 'جشن آغاز اِلدوریا')
        )
        if event is None:
            session.add(GameEvent(
                name='جشن آغاز اِلدوریا',
                description='یک رویداد آزمایشی برای نسخه اولیه.',
                starts_at=now - timedelta(days=1),
                ends_at=now + timedelta(days=30),
                reward_gold=1000, reward_xp=500,
            ))
        await session.commit()
    print('Social systems seeded successfully.')


if __name__ == '__main__':
    from utils.script_runtime import run_script
    run_script(main)
