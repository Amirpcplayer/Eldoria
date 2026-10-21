import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.item import Item


ITEMS = [

    {"name": "🌿 گیاه اِلدوریا", "description": "مادهٔ لازم برای ساخت و ارتقای تجهیزات.", "item_type": "material", "rarity": "common", "sell_price": 20, "buy_price": 80, "is_tradeable": True},
    {"name": "⛏️ تکه‌آهن گابلین", "description": "مادهٔ لازم برای ارتقای تجهیزات سطح متوسط.", "item_type": "material", "rarity": "uncommon", "sell_price": 50, "buy_price": 200, "is_tradeable": True},
    {"name": "💎 خرده‌سنگ جادویی", "description": "مادهٔ لازم برای ارتقای تجهیزات جادویی.", "item_type": "material", "rarity": "rare", "sell_price": 100, "buy_price": 450, "is_tradeable": True},
    {"name": "🔥 فلس اژدها", "description": "مادهٔ کمیاب برای ارتقای تجهیزات سطح بالا.", "item_type": "material", "rarity": "epic", "sell_price": 250, "buy_price": 1000, "is_tradeable": True},
    {"name": "🦴 پنجهٔ گرگ", "description": "مادهٔ ساخت تجهیزات سبک.", "item_type": "material", "rarity": "common", "sell_price": 30, "buy_price": 120, "is_tradeable": True},
    {
        "name": "🧪 معجون سلامتی",
        "description": "❤️ بازیابی ۲۰٪ از حداکثر HP؛ بیشتر از ظرفیت باقی‌مانده پر نمی‌کند.",
        "item_type": "potion",
        "rarity": "common",
        "sell_price": 20,
        "buy_price": 100,
        "is_tradeable": True,
    },
    {
        "name": "🧪 معجون سلامتی بزرگ",
        "description": "❤️ بازیابی ۴۰٪ از حداکثر HP؛ بیشتر از ظرفیت باقی‌مانده پر نمی‌کند.",
        "item_type": "potion",
        "rarity": "rare",
        "sell_price": 50,
        "buy_price": 250,
        "is_tradeable": True,
    },
    {
        "name": "🔷 معجون مانا",
        "description": "🔷 بازیابی ۲۰٪ از حداکثر Mana؛ بیشتر از ظرفیت باقی‌مانده پر نمی‌کند.",
        "item_type": "potion",
        "rarity": "rare",
        "sell_price": 75,
        "buy_price": 300,
        "is_tradeable": True,
    },
    {
        "name": "🧪 معجون مانای بزرگ",
        "description": "🔷 بازیابی ۴۰٪ از حداکثر Mana؛ بیشتر از ظرفیت باقی‌مانده پر نمی‌کند.",
        "item_type": "potion",
        "rarity": "rare",
        "sell_price": 200,
        "buy_price": 800,
        "is_tradeable": True,
    },
    {
        "name": "🗡️ شمشیر آهنی",
        "description": "⚔️ یک سلاح ساده برای شروع ماجراجویی.",
        "item_type": "equipment",
        "rarity": "common",
        "sell_price": 40,
        "buy_price": 0,
        "is_tradeable": True,
    },
    {
        "name": "🗃 سنگ جادویی",
        "description": "💠 یک متریال جادویی مورد استفاده در ارتقا.",
        "item_type": "material",
        "rarity": "uncommon",
        "sell_price": 15,
        "buy_price": 150,
        "is_tradeable": True,
    },
    {
        "name": "🪵 چوب اِلدوری",
        "description": "🪵 چوب مقاوم مورد استفاده در ساخت‌وساز.",
        "item_type": "material",
        "rarity": "common",
        "sell_price": 5,
        "buy_price": 25,
        "is_tradeable": True,
    },
    {
        "name": "⛓️ سنگ آهن",
        "description": "⛓️ سنگ خام مناسب برای ساخت تجهیزات.",
        "item_type": "material",
        "rarity": "common",
        "sell_price": 8,
        "buy_price": 40,
        "is_tradeable": True,
    },
    {
        "name": "💎 کریستال جادویی",
        "description": "💎 کریستالی سرشار از انرژی جادویی.",
        "item_type": "material",
        "rarity": "rare",
        "sell_price": 75,
        "buy_price": 300,
        "is_tradeable": True,
    },
    {
        "name": "🐺 پنجه گرگ",
        "description": "🐺 ماده‌ای کمیاب از شکار گرگ‌های اِلدوریا.",
        "item_type": "material",
        "rarity": "uncommon",
        "sell_price": 30,
        "buy_price": 120,
        "is_tradeable": True,
    },
    {
        "name": "🐉 فلس اژدها",
        "description": "🐉 فلس مقاوم یک اژدها.",
        "item_type": "material",
        "rarity": "epic",
        "sell_price": 250,
        "buy_price": 1000,
        "is_tradeable": True,
    },
    {
        "name": "📜 اسکرول قدرت",
        "description": "به مدت ۲ ساعت، آسیب حملات فیزیکی و جادویی را ۲۰٪ افزایش می‌دهد.",
        "item_type": "scroll",
        "rarity": "rare",
        "sell_price": 60,
        "buy_price": 300,
        "is_tradeable": True,
    },
    {
        "name": "📜 طومار تجربه",
        "description": "✨ یک طومار ارزشمند برای سیستم تجربه.",
        "item_type": "scroll",
        "rarity": "rare",
        "sell_price": 150,
        "buy_price": 750,
        "is_tradeable": True,
    },
    {
        "name": "📜 طومار مهارت",
        "description": "🔮 یک طومار کمیاب برای سیستم مهارت.",
        "item_type": "scroll",
        "rarity": "epic",
        "sell_price": 200,
        "buy_price": 1000,
        "is_tradeable": True,
    },
]


async def seed_items() -> None:
    added = 0
    updated = 0

    async with AsyncSessionLocal() as session:
        for item_data in ITEMS:
            existing_item = await session.scalar(
                select(Item).where(Item.name == item_data["name"])
            )

            if existing_item is None:
                session.add(Item(**item_data))
                added += 1
                continue

            changed = False
            for key, value in item_data.items():
                if getattr(existing_item, key) != value:
                    setattr(existing_item, key, value)
                    changed = True

            if changed:
                updated += 1

        await session.commit()

    print(
        "✅ Items seeded successfully. "
        f"Added: {added}, Updated: {updated}"
    )


if __name__ == "__main__":
    asyncio.run(seed_items())
