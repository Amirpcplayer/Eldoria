import asyncio
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from database.redis import redis


BATTLE_ID = "6b20753e0eb44a6499b21f27512f10bb"


async def main():
    key = f"eldoria:battle:{BATTLE_ID}"

    deleted = await redis.delete(key)

    print("=" * 40)

    if deleted:
        print("STALE BATTLE CLEARED")
        print(f"Key: {key}")
    else:
        print("BATTLE NOT FOUND")
        print(f"Key: {key}")

    print("=" * 40)


if __name__ == "__main__":
    asyncio.run(main())