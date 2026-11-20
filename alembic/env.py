"""Alembic environment for World Eldoria.

Loads every SQLAlchemy model before exposing Base.metadata and derives the
synchronous migration URL from the application's configured database URL.
The application itself continues to use its async database driver.
"""
from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import settings  # noqa: E402
from database.database import Base  # noqa: E402

# Import all models so every table is registered in Base.metadata.
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
from models.social_systems import PlayerSetting, Party, PartyMember, Guild, GuildMember, DungeonRun, PvpChallenge, CraftRecipe, Pet, CharacterPet, GameEvent, GroupDungeonState, GuildMaterial  # noqa: F401,E402
from models.world_systems import WorldBoss, WorldBossContribution, MarketListing, CharacterBestiary, CharacterActivity, DailyTaskProgress, NotificationEvent, PvpRating  # noqa: F401,E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _sync_database_url() -> str:
    """Convert the app URL to a sync URL supported by Alembic's engine."""
    url = make_url(settings.database_url)
    driver = url.drivername
    if driver == "postgresql+asyncpg":
        url = url.set(drivername="postgresql+psycopg")
    elif driver == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    elif driver.startswith("postgresql+") and driver != "postgresql+psycopg":
        raise RuntimeError(
            "Unsupported synchronous Alembic database driver: " + driver
        )
    # Alembic Config uses ConfigParser interpolation; escape percent signs.
    return url.render_as_string(hide_password=False).replace("%", "%%")


config.set_main_option("sqlalchemy.url", _sync_database_url())
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
