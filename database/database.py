# database/database.py

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings
from middlewares.performance_monitor import install_slow_query_logging


# SQLite's default pool differs across SQLAlchemy 2.0 releases.  Keep the
# production pool tuning for network databases and let the dialect choose its
# compatible pool for the standalone SQLite launcher.
_engine_options = {"echo": False, "pool_pre_ping": True}
if not settings.database_url.lower().startswith(("sqlite:", "sqlite+")):
    _engine_options.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
    )

engine = create_async_engine(settings.database_url, **_engine_options)
install_slow_query_logging(engine)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass

async def create_all_tables() -> int:
    """Create missing ORM tables for local/standalone startup.

    Production deployments should still apply Alembic migrations first;
    ``create_all`` creates absent tables but intentionally does not mutate
    existing schemas. Importing the model modules here also makes this helper
    safe to call outside ``main.py`` before handler imports have registered them.
    """
    from importlib import import_module

    for module_name in (
        "models.adventure",
        "models.character",
        "models.character_skill",
        "models.equipment",
        "models.fan_art",
        "models.inventory",
        "models.item",
        "models.monster",
        "models.quest",
        "models.skill",
        "models.social_systems",
        "models.trade",
        "models.world_systems",
    ):
        import_module(module_name)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return len(Base.metadata.tables)
