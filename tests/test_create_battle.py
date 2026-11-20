import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from services.combat_service import create_battle
from database.redis import redis


TELEGRAM_ID = 8252584456
ENEMY_ID = 1


async def main():
    print("=" * 60)
    print("TEST CREATE BATTLE")
    print("=" * 60)

    try:
        result = await create_battle(
            TELEGRAM_ID,
            ENEMY_ID,
        )

        print()
        print("RESULT:")
        print(result)

    except Exception as e:
        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)
        print(f"{type(e).__name__}: {e}")

        import traceback

        traceback.print_exc()

        return

    print()
    print("=" * 60)
    print("REDIS BATTLE KEYS")
    print("=" * 60)

    async for key in redis.scan_iter(
        match="eldoria:battle:*"
    ):
        if isinstance(key, bytes):
            key = key.decode("utf-8")

        print(key)

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())