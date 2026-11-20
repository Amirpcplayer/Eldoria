"""Populate the standalone game's initial catalogs in the configured database.

For Windows standalone mode, run setup_game_content.bat from the project folder.
The batch file pins DATABASE_URL to the same SQLite file used by run_game.bat.
This setup is intended to be safe to repeat: catalog seeders insert missing rows
and update only the catalog fields they own; player inventory and characters are
not reset.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import func, select

from database.database import AsyncSessionLocal, create_all_tables, engine
from models.adventure import AdventureArea, AdventureEnemy
from models.equipment import Equipment
from models.item import Item
from models.monster import Monster
from models.quest import Quest
from models.skill import Skill
from models.social_systems import CraftRecipe, GameEvent, Pet
from services.monster_seed import seed_monsters
from utils.link_adventure_monsters import link_adventure_monsters
from utils.seed_adventure import seed as seed_adventure
from utils.seed_crafting import seed as seed_crafting
from utils.seed_equipment import seed_equipment
from utils.seed_items import seed_items
from utils.seed_quests import seed_quests
from utils.seed_skills import seed_skills
from utils.seed_social_systems import main as seed_social_systems

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def _count(model) -> int:
    async with AsyncSessionLocal() as session:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def setup_game_content() -> None:
    print("\n=== World Eldoria: Initial Game Content Setup ===", flush=True)
    print("[1/10] Creating missing database tables...", flush=True)
    table_count = await create_all_tables()
    print(f"      Database schema ready ({table_count} tables).", flush=True)

    print("[2/10] Seeding monster catalog...", flush=True)
    monster_count = await seed_monsters()
    print(f"      Monster variants processed: {monster_count}", flush=True)

    print("[3/10] Seeding adventure zones and enemies...", flush=True)
    await seed_adventure()
    linked_count = await link_adventure_monsters()
    print(f"      Adventure enemy-to-monster links: {linked_count}", flush=True)

    print("[4/10] Seeding items and materials...", flush=True)
    await seed_items()

    print("[5/10] Seeding equipment catalog...", flush=True)
    await seed_equipment()

    print("[6/10] Seeding skills...", flush=True)
    await seed_skills()

    print("[7/10] Seeding quests...", flush=True)
    await seed_quests()

    print("[8/10] Seeding crafting recipes...", flush=True)
    await seed_crafting()

    print("[9/10] Seeding pets and the starter event...", flush=True)
    await seed_social_systems()

    print("[10/10] Checking visible catalog counts...", flush=True)
    counts = (
        ("Adventure areas", AdventureArea),
        ("Adventure enemies", AdventureEnemy),
        ("Monster catalog", Monster),
        ("Items/materials", Item),
        ("Equipment", Equipment),
        ("Skills", Skill),
        ("Quests", Quest),
        ("Crafting recipes", CraftRecipe),
        ("Pets", Pet),
        ("Events", GameEvent),
    )
    for label, model in counts:
        print(f"      {label}: {await _count(model)}", flush=True)

    print("\n✅ Initial game content setup completed.", flush=True)
    print("Start/restart the bot, open /menu, then choose 🗺️ ماجراجویی → مناطق ماجراجویی.", flush=True)


async def main() -> None:
    try:
        await setup_game_content()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
