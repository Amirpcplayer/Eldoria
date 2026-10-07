import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.item import Item


ITEMS = [
    {
        "name": "🧪 معجون سلامتی",
        "description": "❤️ مقدار 40 واحد HP بازیابی می‌کند.",
        "item_type": "potion",
        "rarity": "common",
        "sell_price": 20,
        "is_tradeable": True,
    },
    {
        "name": "🧪 معجون سلامتی بزرگ",
        "description": "❤️ مقدار 80 واحد HP بازیابی می‌کند.",
        "item_type": "potion",
        "rarity": "rare",
        "sell_price": 50,
        "is_tradeable": True,
    },
    {
        "name": "🗡️ شمشیر آهنی",
        "description": "⚔️ یک سلاح ساده برای شروع ماجراجویی.",
        "item_type": "equipment",
        "rarity": "common",
        "sell_price": 40,
        "is_tradeable": True,
    },
    {
        "name": "📦 سنگ جادویی",
        "description": "💠 یک متریال جادویی مورد استفاده در ارتقا.",
        "item_type": "material",
        "rarity": "uncommon",
        "sell_price": 15,
        "is_tradeable": True,
    },
    {
        "name": "📜 اسکرول قدرت",
        "description": "✨ یک اسکرول جادویی ناشناخته.",
        "item_type": "scroll",
        "rarity": "rare",
        "sell_price": 60,
        "is_tradeable": True,
    },
]


async def seed_items():

    async with AsyncSessionLocal() as session:

        for item_data in ITEMS:

            existing_item = await session.scalar(
                select(Item).where(
                    Item.name == item_data["name"]
                )
            )

            if existing_item:
                continue

            item = Item(**item_data)

            session.add(item)

        await session.commit()

    print("✅ Items seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_items())