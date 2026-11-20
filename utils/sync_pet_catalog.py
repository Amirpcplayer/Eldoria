"""Add the ten requested pets to the live database without touching player ownership.
Run once with: python -m utils.sync_pet_catalog
"""
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from database.database import AsyncSessionLocal
from models.social_systems import Pet

PETS = (
    ('🐺 گرگ اِلدوری', 'common', 3, 2, 10, 500),
    ('🐉 اژدهای کوچک', 'rare', 8, 5, 25, 2500),
    ('🦄 تک‌شاخ نورانی', 'epic', 5, 8, 40, 7000),
    ('🔥 ققنوس جاودان', 'legendary', 9, 6, 35, 9000),
    ('🐕 سگ جهنمی', 'epic', 10, 4, 28, 7500),
    ('🌙 پلنگ سایه', 'rare', 7, 4, 22, 3500),
    ('❄️ گریفین یخی', 'epic', 8, 7, 32, 8000),
    ('⚡ رعدبال', 'rare', 9, 3, 20, 4500),
    ('🌿 نگهبان جنگل', 'epic', 6, 9, 45, 6500),
    ('🌌 اژدهای اختری', 'legendary', 12, 8, 48, 12000),
)

async def seed_pets(session):
    """Stage missing pets in the caller's transaction, preserving existing stats."""
    added = 0
    for name, rarity, attack, defense, hp, price in PETS:
        existing = await session.scalar(select(Pet).where(Pet.name == name))
        if existing is None:
            session.add(Pet(name=name, rarity=rarity, bonus_attack=attack,
                            bonus_defense=defense, bonus_hp=hp, price=price,
                            is_active=True))
            added += 1
        elif not existing.is_active:
            existing.is_active = True
    await session.flush()
    return added


async def main():
    async with AsyncSessionLocal() as session:
        added = await seed_pets(session)
        # Snapshot before commit: expired ORM attributes may trigger MissingGreenlet.
        visible = (await session.scalars(select(Pet).where(Pet.is_active.is_(True)))).all()
        rows = [(pet.id, pet.name) for pet in visible]
        await session.commit()
    print(f'Added: {added}; active pets in database: {len(rows)}')
    for pet_id, name in rows:
        print(f'{pet_id}: {name}')


if __name__ == '__main__':
    from utils.script_runtime import run_script
    run_script(main)
