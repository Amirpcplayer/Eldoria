import asyncio

from services.monster_seed import seed_monsters


async def main():
    count = await seed_monsters()

    print(
        f"Monster seed completed: {count} monsters processed."
    )


if __name__ == "__main__":
    asyncio.run(main())