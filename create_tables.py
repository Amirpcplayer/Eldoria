"""Create all registered model tables for local development only.

For existing installations, use `alembic upgrade head` so schema changes are
tracked and applied in the correct order. This script does not replace Alembic.
"""
import asyncio

from database.database import Base, engine

# Import every model before create_all so SQLAlchemy registers all tables.
from models.character import Character  # noqa: F401,E402
from models.character_skill import CharacterSkill  # noqa: F401,E402
from models.equipment import Equipment, CharacterEquipment  # noqa: F401,E402
from models.inventory import Inventory  # noqa: F401,E402
from models.item import Item  # noqa: F401,E402
from models.trade import Trade  # noqa: F401,E402
from models.skill import Skill  # noqa: F401,E402
from models.adventure import AdventureArea, AdventureEnemy  # noqa: F401,E402
from models.monster import Monster  # noqa: F401,E402
from models.fan_art import FanArt, FanArtOrder, FanArtOwnership  # noqa: F401,E402
from models.quest import Quest, CharacterQuest  # noqa: F401,E402


async def create_tables() -> None:
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        print("Database tables created successfully.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())
