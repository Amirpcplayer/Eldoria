import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character


async def main():
    async with AsyncSessionLocal() as session:

        print("=" * 80)
        print("تمام قهرمانها")
        print("=" * 80)

        result = await session.execute(
            select(Character).order_by(Character.id)
        )

        characters = result.scalars().all()

        for character in characters:
            print(
                f"ID={character.id} | "
                f"Telegram ID={character.telegram_id} | "
                f"Username={character.telegram_username!r} | "
                f"Name={character.name!r}"
            )

        print("=" * 80)
        print()

        username = input(
            "Username را وارد کن (مثلاً leaderf2f): "
        ).strip().lstrip("@").lower()

        result = await session.execute(
            select(Character).where(
                Character.telegram_username == username
            )
        )

        character = result.scalar_one_or_none()

        print()

        if character:
            print("✅ USERNAME پیدا شد")
            print(f"Character ID : {character.id}")
            print(f"Telegram ID  : {character.telegram_id}")
            print(f"Username     : @{character.telegram_username}")
            print(f"Character    : {character.name}")
        else:
            print("❌ این username در دیتابیس ثبت نشده است.")
            print()
            print(
                "اگر این بازیکن قبلاً قهرمان ساخته، "
                "باید خودش یک بار با ربات تعامل کند تا username او ثبت شود."
            )


if __name__ == "__main__":
    asyncio.run(main())