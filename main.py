import asyncio

import models.monster

from aiogram import Dispatcher

from bot.bot import bot

from handlers.start import router as start_router
from handlers.main_menu import router as main_menu_router
from handlers.character_creation import router as character_creation_router
from handlers.race import router as race_router
from handlers.element import router as element_router
from handlers.admin_temp import router as admin_temp_router
from handlers.inventory import router as inventory_router
from handlers.profile import router as profile_router
from handlers.skills import router as skills_router
from handlers.equipment import router as equipment_router
from handlers.quest import router as quest_router
from handlers.shop import router as shop_router
from handlers.fan_art import router as fan_art_router
from handlers.fan_art_admin import router as fan_art_admin_router
from handlers.combat import router as combat_router
from handlers.adventure import router as adventure_router


dp = Dispatcher()


dp.include_router(start_router)
dp.include_router(character_creation_router)
dp.include_router(race_router)
dp.include_router(element_router)
dp.include_router(admin_temp_router)

dp.include_router(main_menu_router)
dp.include_router(shop_router)

dp.include_router(inventory_router)
dp.include_router(profile_router)
dp.include_router(skills_router)
dp.include_router(equipment_router)
dp.include_router(quest_router)

dp.include_router(fan_art_admin_router)
dp.include_router(fan_art_router)

dp.include_router(combat_router)
dp.include_router(adventure_router)


async def main():
    print("World Eldoria is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())