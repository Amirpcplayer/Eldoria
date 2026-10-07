import asyncio

from database.database import Base, engine
from models.character import Character


async def create_tables():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    print("✅ Database tables created successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())