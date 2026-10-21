from __future__ import annotations

import asyncio
import json

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.item import Item
from models.social_systems import CraftRecipe
from models.equipment import Equipment
from utils.seed_equipment import seed_equipment


ITEMS = [
    {"name": "🪵 چوب اِلدوری", "description": "چوب مقاوم برای ساخت‌وساز.", "item_type": "material", "rarity": "common", "sell_price": 5, "buy_price": 25, "is_tradeable": True},
    {"name": "⛓️ سنگ آهن", "description": "سنگ آهن موردنیاز کارگاه.", "item_type": "material", "rarity": "common", "sell_price": 8, "buy_price": 40, "is_tradeable": True},
    {"name": "🗃 سنگ جادویی", "description": "سنگی با انرژی جادویی.", "item_type": "material", "rarity": "uncommon", "sell_price": 15, "buy_price": 150, "is_tradeable": True},
    {"name": "💎 کریستال جادویی", "description": "کریستال سرشار از Mana.", "item_type": "material", "rarity": "rare", "sell_price": 75, "buy_price": 300, "is_tradeable": True},
    {"name": "🧪 معجون سلامتی", "description": "۵٬۰۰۰ واحد HP بازیابی می‌کند.", "item_type": "potion", "rarity": "common", "sell_price": 20, "buy_price": 100, "is_tradeable": True},
    {"name": "🧪 معجون سلامتی بزرگ", "description": "۲۵٬۰۰۰ واحد HP بازیابی می‌کند.", "item_type": "potion", "rarity": "rare", "sell_price": 50, "buy_price": 250, "is_tradeable": True},
    {"name": "🔷 معجون مانا", "description": "۵٬۰۰۰ واحد Mana بازیابی می‌کند.", "item_type": "potion", "rarity": "rare", "sell_price": 75, "buy_price": 300, "is_tradeable": True},
    {"name": "📜 اسکرول قدرت", "description": "به مدت ۲ ساعت، آسیب حملات فیزیکی و جادویی را ۲۰٪ افزایش می‌دهد.", "item_type": "scroll", "rarity": "rare", "sell_price": 60, "buy_price": 300, "is_tradeable": True},
    {"name": "🦴 پنجهٔ گرگ", "description": "متریال افتاده از خانوادهٔ گرگ‌ها؛ مناسب دستورهای شکارچی.", "item_type": "material", "rarity": "common", "sell_price": 12, "buy_price": 0, "is_tradeable": True},
    {"name": "⛏️ تکه‌آهن گابلین", "description": "آهن بازیابی‌شده از تجهیزات گابلین.", "item_type": "material", "rarity": "uncommon", "sell_price": 25, "buy_price": 0, "is_tradeable": True},
    {"name": "💎 خرده‌سنگ جادویی", "description": "خرده‌ای از هستهٔ سنگی گولم.", "item_type": "material", "rarity": "rare", "sell_price": 40, "buy_price": 0, "is_tradeable": True},
    {"name": "🔥 فلس اژدها", "description": "متریال کمیاب برای ارتقای تجهیزات سطح بالا.", "item_type": "material", "rarity": "epic", "sell_price": 100, "buy_price": 0, "is_tradeable": True},
    {"name": "🌿 گیاه اِلدوریا", "description": "گیاه جمع‌آوری‌شده در ماجراجویی و متریال ارتقای اولیه.", "item_type": "material", "rarity": "common", "sell_price": 10, "buy_price": 0, "is_tradeable": True},
    {"name": "📜 اسکرول شکارچی", "description": "به مدت ۲ ساعت، پاداش XP و Gold ماجراجویی و شانس یافتن متریال را ۳۰٪ افزایش می‌دهد.", "item_type": "scroll", "rarity": "uncommon", "sell_price": 35, "buy_price": 0, "is_tradeable": True},
    {"name": "📜 اسکرول دفاع", "description": "به مدت ۲ ساعت، آسیب دریافتی از دشمنان را ۲۰٪ کاهش می‌دهد.", "item_type": "scroll", "rarity": "rare", "sell_price": 60, "buy_price": 300, "is_tradeable": True},
    {"name": "📜 اسکرول مقاومت", "description": "به مدت ۲ ساعت، مقاومت عنصری دشمن را هنگام جادو نادیده می‌گیرد.", "item_type": "scroll", "rarity": "rare", "sell_price": 60, "buy_price": 300, "is_tradeable": True},
    {"name": "📜 اسکرول درمان", "description": "به مدت ۲ ساعت، اثر بازیابی HP را ۲۰٪ افزایش می‌دهد.", "item_type": "scroll", "rarity": "rare", "sell_price": 60, "buy_price": 300, "is_tradeable": True},
    {"name": "📜 اسکرول مانا", "description": "به مدت ۲ ساعت، اثر بازیابی Mana را ۲۰٪ افزایش می‌دهد.", "item_type": "scroll", "rarity": "rare", "sell_price": 60, "buy_price": 300, "is_tradeable": True},
]

RECIPES = [
    {"name": "معجون سلامتی کوچک", "output": "🧪 معجون سلامتی", "gold": 20, "level": 1, "materials": {"⛓️ سنگ آهن": 1, "🪵 چوب اِلدوری": 1}},
    {"name": "معجون سلامتی بزرگ", "output": "🧪 معجون سلامتی بزرگ", "gold": 60, "level": 5, "materials": {"⛓️ سنگ آهن": 2, "🗃 سنگ جادویی": 1}},
    {"name": "معجون مانا", "output": "🔷 معجون مانا", "gold": 75, "level": 5, "materials": {"🗃 سنگ جادویی": 2, "💎 کریستال جادویی": 1}},
    {"name": "اسکرول قدرت", "output": "📜 اسکرول قدرت", "gold": 100, "level": 8, "materials": {"🗃 سنگ جادویی": 2, "💎 کریستال جادویی": 1, "🪵 چوب اِلدوری": 1}},
    {"name": "اسکرول دفاع", "output": "📜 اسکرول دفاع", "gold": 100, "level": 8, "materials": {"⛓️ سنگ آهن": 2, "🗃 سنگ جادویی": 1}},
    {"name": "اسکرول مقاومت", "output": "📜 اسکرول مقاومت", "gold": 125, "level": 12, "materials": {"🗃 سنگ جادویی": 2, "💎 کریستال جادویی": 1}},
    {"name": "اسکرول درمان", "output": "📜 اسکرول درمان", "gold": 100, "level": 6, "materials": {"🌿 گیاه اِلدوریا": 3, "🪵 چوب اِلدوری": 1}},
    {"name": "اسکرول مانا", "output": "📜 اسکرول مانا", "gold": 100, "level": 6, "materials": {"💎 کریستال جادویی": 1, "🪵 چوب اِلدوری": 1}},
    {"name": "کلاه آهنی کارگاه", "output_equipment": "🪖 کلاه آهنی", "gold": 100, "level": 1, "materials": {"⛓️ سنگ آهن": 4, "🪵 چوب اِلدوری": 1}},
    {"name": "اسکرول شکارچی گرگ", "output": "📜 اسکرول شکارچی", "gold": 75, "level": 3, "materials": {"🦴 پنجهٔ گرگ": 2, "🪵 چوب اِلدوری": 1}},
]


async def seed() -> None:
    await seed_equipment()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for item_data in ITEMS:
                item = await session.scalar(select(Item).where(Item.name == item_data["name"]))
                if item is None:
                    item = Item(**item_data)
                    session.add(item)
                else:
                    for key, value in item_data.items():
                        setattr(item, key, value)
            await session.flush()

            ids = {}
            for item_data in ITEMS:
                item = await session.scalar(select(Item).where(Item.name == item_data["name"]))
                ids[item.name] = item.id

            for recipe_data in RECIPES:
                materials = {str(ids[name]): amount for name, amount in recipe_data["materials"].items()}
                recipe = await session.scalar(select(CraftRecipe).where(CraftRecipe.name == recipe_data["name"]))
                equipment_id = None
                result_item_id = ids.get(recipe_data.get("output", ""))
                if recipe_data.get("output_equipment"):
                    equipment = await session.scalar(select(Equipment).where(Equipment.name == recipe_data["output_equipment"]))
                    if equipment is None:
                        continue
                    equipment_id = equipment.id
                values = {
                    "name": recipe_data["name"],
                    "result_item_id": result_item_id,
                    "result_equipment_id": equipment_id,
                    "gold_cost": recipe_data["gold"],
                    "materials_json": json.dumps(materials, ensure_ascii=False),
                    "required_level": recipe_data["level"],
                    "is_active": True,
                }
                if recipe is None:
                    session.add(CraftRecipe(**values))
                else:
                    for key, value in values.items():
                        setattr(recipe, key, value)
    print("Crafting recipes and materials seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
