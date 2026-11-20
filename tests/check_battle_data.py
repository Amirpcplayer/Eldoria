import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.redis import redis
from models.character import Character


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Character).where(
                Character.name == "AMIR"
            )
        )

        character = result.scalar_one_or_none()

        if character is None:
            print("❌ AMIR not found.")
            return

        print("=" * 60)
        print("CHARACTER")
        print("=" * 60)
        print(f"ID:       {character.id}")
        print(f"Name:     {character.name}")
        print(f"Telegram: {character.telegram_id}")
        print(f"HP:       {character.hp}/{character.max_hp}")
        print(f"Mana:     {character.mana}/{character.max_mana}")

        print()
        print("=" * 60)
        print("REDIS BATTLE KEYS")
        print("=" * 60)

        battle_keys = []

        async for key in redis.scan_iter(
            match="eldoria:battle:*"
        ):
            if isinstance(key, bytes):
                key = key.decode("utf-8")

            battle_keys.append(key)

        if not battle_keys:
            print("❌ No battle keys found.")
            return

        for key in sorted(battle_keys):
            print()
            print(f"KEY: {key}")

            key_type = await redis.type(key)

            if isinstance(key_type, bytes):
                key_type = key_type.decode("utf-8")

            print(f"TYPE: {key_type}")

            if key_type == "hash":
                data = await redis.hgetall(key)

                print("DATA:")

                for field, value in data.items():
                    if isinstance(field, bytes):
                        field = field.decode("utf-8")

                    if isinstance(value, bytes):
                        value = value.decode("utf-8")

                    print(f"  {field}: {value}")

            elif key_type == "string":
                value = await redis.get(key)

                if isinstance(value, bytes):
                    value = value.decode("utf-8")

                print(f"VALUE: {value}")

            else:
                print(
                    f"⚠️ Redis type '{key_type}' "
                    "is not a hash or string."
                )

        print()
        print("=" * 60)
        print("DONE")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())