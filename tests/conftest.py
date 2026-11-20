"""Shared test configuration; use safe local placeholders when .env is absent."""
import os

# Settings are instantiated at import time by several modules. These values are
# test-only placeholders; tests must never contact Telegram or production services.
os.environ.setdefault("BOT_TOKEN", "123456789:TEST_ONLY_TOKEN_NOT_VALID")
# Tests must be isolated from any local or production services by default.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("ADMIN_ID", "1")

import pytest


@pytest.fixture(scope="session", autouse=True)
def _pytest_session_marker():
    yield


@pytest.fixture(scope="session", autouse=True)
async def _bootstrap_sqlite_test_schema():
    """Create the ORM schema automatically only for explicitly selected SQLite tests.

    CI and developers can use a disposable SQLite file for service-level tests
    without needing a running PostgreSQL server. The default PostgreSQL test URL
    is not modified and never gets auto-created here.
    """
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.lower().startswith(("sqlite:", "sqlite+")):
        yield
        return

    from database.database import create_all_tables, engine

    await create_all_tables()
    # Service tests expect the game's baseline catalog. Seed only disposable,
    # explicitly selected SQLite test databases, never production PostgreSQL.
    from services.monster_seed import seed_monsters
    from utils.seed_adventure import seed as seed_adventure
    from utils.seed_skills import seed_skills
    from utils.seed_quests import seed_quests
    from utils.seed_equipment import seed_equipment

    await seed_monsters()
    await seed_adventure()
    await seed_skills()
    await seed_equipment()
    await seed_quests()
    try:
        yield
    finally:
        await engine.dispose()
