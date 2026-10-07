import asyncio
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Character)
        )

        characters = result.scalars().all()

        if not characters:
            print("❌ No characters found.")
            return

        print("=" * 50)
        print("CHARACTER STATS")
        print("=" * 50)

        for character in characters:
            print(f"ID:          {character.id}")
            print(f"Name:        {character.name}")
            print(f"Telegram ID: {character.telegram_id}")
            print(f"Level:       {character.level}")
            print(f"XP:          {character.xp}")
            print(f"Gold:        {character.gold}")
            print()
            print(f"HP:          {character.hp}")
            print(f"Max HP:      {character.max_hp}")
            print(f"Mana:        {character.mana}")
            print(f"Max Mana:    {character.max_mana}")
            print()
            print(f"Attack:      {character.attack}")
            print(f"Magic Power: {character.magic_power}")
            print(f"Defense:     {character.defense}")
            print(f"Magic Def:   {character.magic_defense}")
            print(f"Speed:       {character.speed}")
            print(f"Accuracy:    {character.accuracy}")
            print(f"Luck:        {character.luck}")
            print(f"Critical:    {character.critical}")
            print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())