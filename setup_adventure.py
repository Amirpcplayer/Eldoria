"""One-command database migration, table setup, seeding and adventure linking."""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

def run_migrations():
    # Alembic tracks schema changes for both new and existing installations.
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True)

async def seed_all():
    from services.monster_seed import seed_monsters
    from utils.seed_adventure import seed
    from utils.link_adventure_monsters import link_adventure_monsters
    monster_count = await seed_monsters()
    print(f"Monster seed: {monster_count} processed")
    await seed()
    linked = await link_adventure_monsters()
    print(f"Adventure links: {linked} verified")

def main():
    run_migrations()
    asyncio.run(seed_all())
    print("World Eldoria adventure database setup completed successfully.")

if __name__ == "__main__":
    main()
