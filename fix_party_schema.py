import asyncio

from sqlalchemy import text
from database.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                text("""
                    ALTER TABLE parties
                    ADD COLUMN IF NOT EXISTS title
                    VARCHAR(40) NOT NULL DEFAULT 'ماجراجویان'
                """)
            )

            await session.execute(
                text("""
                    ALTER TABLE parties
                    ADD COLUMN IF NOT EXISTS description
                    TEXT NOT NULL DEFAULT ''
                """)
            )

            await session.commit()
            print("Party schema updated successfully.")

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())