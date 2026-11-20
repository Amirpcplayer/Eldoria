"""Sync one or all static World Eldoria catalogs into the configured database.

Run with the bot stopped. Safe to repeat: this calls the project's existing
idempotent seeders and never deletes player characters, inventories, quests,
or pet ownership.

Examples:
  python sync_catalogs.py all
  python sync_catalogs.py equipment
  python sync_catalogs.py adventure
"""
from __future__ import annotations

import argparse
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
from models.fan_art import FanArt, FanArtOrder, FanArtOwnership

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

CATALOGS = (
    ("Adventure areas", AdventureArea),
    ("Adventure enemies", AdventureEnemy),
    ("Monster variants", Monster),
    ("Items and materials", Item),
    ("Equipment", Equipment),
    ("Skills", Skill),
    ("Quests", Quest),
    ("Crafting recipes", CraftRecipe),
    ("Pets", Pet),
    ("Events", GameEvent),
    ("Fan Art catalog entries", FanArt),
)


async def _seed_monsters() -> None:
    from services.monster_seed import seed_monsters

    count = await seed_monsters()
    print(f"  Monster variants processed: {count}", flush=True)


async def _seed_adventure() -> None:
    from utils.link_adventure_monsters import link_adventure_monsters
    from utils.seed_adventure import seed as seed_adventure

    await seed_adventure()
    count = await link_adventure_monsters()
    print(f"  Adventure enemies linked to monsters: {count}", flush=True)


async def _seed_items() -> None:
    from utils.seed_items import seed_items

    await seed_items()


async def _seed_equipment() -> None:
    from utils.seed_equipment import seed_equipment
    from utils.sync_equipment_catalog import main as sync_extra_equipment

    await seed_equipment()
    # Include the additional tier/slot entries that are not in the base seed.
    await sync_extra_equipment()


async def _seed_skills() -> None:
    from utils.seed_skills import seed_skills

    await seed_skills()


async def _seed_quests_with_prerequisites() -> None:
    from utils.seed_quests import seed_quests

    # Quest targets refer to enemies and skills, so ensure both dependencies exist.
    await _seed_monsters()
    await _seed_adventure()
    await _seed_skills()
    await seed_quests()


async def _seed_crafting_with_prerequisites() -> None:
    from utils.seed_crafting import seed as seed_crafting

    await _seed_items()
    await _seed_equipment()
    await seed_crafting()


async def _seed_pets_events() -> None:
    from utils.seed_social_systems import main as seed_social_systems

    await seed_social_systems()



async def _check_fan_art_catalog() -> None:
    """Report the database-backed Fan Art catalog without inventing fake entries.

    Fan Art records need a real Telegram photo file_id; unlike static game catalogs,
    this catalog is populated by an administrator through /fanart_add.
    """
    async with AsyncSessionLocal() as session:
        total = int(await session.scalar(select(func.count()).select_from(FanArt)) or 0)
        active = int(
            await session.scalar(
                select(func.count()).select_from(FanArt).where(FanArt.is_active.is_(True))
            ) or 0
        )
        ownerships = int(
            await session.scalar(select(func.count()).select_from(FanArtOwnership)) or 0
        )
        orders = int(
            await session.scalar(select(func.count()).select_from(FanArtOrder)) or 0
        )

    print("\nFan Art catalog status:", flush=True)
    print(f"  Catalog entries: {total}", flush=True)
    print(f"  Active entries: {active}", flush=True)
    print(f"  Ownership records: {ownerships}", flush=True)
    print(f"  Order history records: {orders}", flush=True)
    if total == 0:
        print(
            "  ⚠️ The Fan Art catalog is empty. No fake items were generated because "
            "each entry requires a real Telegram photo file_id.",
            flush=True,
        )
        print(
            "  To populate it: open the bot's private chat as an admin, send "
            "/fanart_add, upload a Photo, then follow the prompts for name, rarity, "
            "price, limited stock, and quantity.",
            flush=True,
        )
    elif active == 0:
        print(
            "  ⚠️ Entries exist, but all are inactive. Activate at least one Fan Art "
            "entry in the admin tools before it appears in the shop or group hunt.",
            flush=True,
        )
    else:
        print(
            "  ✅ Active Fan Art entries are available to the shop/group hunt.",
            flush=True,
        )
        if ownerships == 0:
            print(
                "  ℹ️ No player owns any Fan Art yet. A catalog entry is not the same "
                "as ownership; users must buy, claim, or receive a Fan Art.",
                flush=True,
            )


async def _sync_all() -> None:
    print("[1/9] Monster catalog", flush=True)
    await _seed_monsters()
    print("[2/9] Adventure zones and enemy links", flush=True)
    await _seed_adventure()
    print("[3/9] Items and materials", flush=True)
    await _seed_items()
    print("[4/9] Equipment catalog and extra tiers", flush=True)
    await _seed_equipment()
    print("[5/9] Skill catalog", flush=True)
    await _seed_skills()
    print("[6/9] Quests", flush=True)
    from utils.seed_quests import seed_quests
    await seed_quests()
    print("[7/9] Crafting recipes", flush=True)
    from utils.seed_crafting import seed as seed_crafting
    await seed_crafting()
    print("[8/9] Pets and starter event", flush=True)
    await _seed_pets_events()
    print("[9/9] Fan Art catalog status (dynamic catalog)", flush=True)
    await _check_fan_art_catalog()


async def _count(model) -> int:
    async with AsyncSessionLocal() as session:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def sync_catalog(category: str) -> None:
    print("\n=== World Eldoria catalog synchronization ===", flush=True)
    print(f"Selection: {category}", flush=True)
    print("Database: the DATABASE_URL selected by the launcher", flush=True)
    print("Creating any missing tables...", flush=True)
    table_count = await create_all_tables()
    print(f"Schema ready ({table_count} tables).\n", flush=True)

    if category == "all":
        await _sync_all()
    elif category == "monsters":
        await _seed_monsters()
    elif category == "adventure":
        await _seed_monsters()
        await _seed_adventure()
    elif category == "items":
        await _seed_items()
    elif category == "equipment":
        await _seed_equipment()
    elif category == "skills":
        await _seed_skills()
    elif category == "quests":
        await _seed_quests_with_prerequisites()
    elif category == "crafting":
        await _seed_crafting_with_prerequisites()
    elif category == "pets-events":
        await _seed_pets_events()
    elif category == "fanart":
        await _check_fan_art_catalog()

    print("\nCatalog totals currently in the selected database:", flush=True)
    for label, model in CATALOGS:
        print(f"  {label}: {await _count(model)}", flush=True)
    print("\n✅ Catalog synchronization completed.", flush=True)
    print("Player character/inventory rows are not cleared by this tool.", flush=True)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize World Eldoria catalogs.")
    parser.add_argument(
        "catalog",
        nargs="?",
        default="all",
        choices=("all", "monsters", "adventure", "items", "equipment", "skills", "quests", "crafting", "pets-events", "fanart"),
        help="which catalog to sync (default: all)",
    )
    args = parser.parse_args()
    try:
        await sync_catalog(args.catalog)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
