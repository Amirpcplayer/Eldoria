from __future__ import annotations

import asyncio
import logging

import models.monster
import models.social_systems  # register social and group-dungeon models
import models.world_systems  # register progression, marketplace and world-boss models

from aiogram import Dispatcher
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeDefault, ErrorEvent

from bot.bot import bot
from database.database import engine, AsyncSessionLocal
from models.character import Character
from sqlalchemy import select
from database.redis import redis
from middlewares.performance_monitor import UpdateTimingMiddleware

from middlewares.username_sync import UsernameSyncMiddleware
from middlewares.panel_owner import PanelOwnerMiddleware
from middlewares.delete_main_menu_on_click import DeleteMainMenuOnClickMiddleware
from middlewares.character_required import CharacterRequiredMiddleware
from middlewares.adventure_fight_lock import AdventureFightLockMiddleware

from handlers.group_guardian import router as guardian_router, GuardianMiddleware
from handlers.start import router as start_router
from handlers.command_aliases import router as command_aliases_router
from handlers.main_menu import router as main_menu_router
from handlers.character_creation import router as character_creation_router
from handlers.race import router as race_router
from handlers.element import router as element_router
from handlers.admin_temp import router as admin_temp_router
from handlers.admin_premium_emoji import router as admin_premium_emoji_router
from handlers.admin_resource_gifts import router as admin_resource_gifts_router
from handlers.fan_art_gifts import router as fan_art_gifts_router
from handlers.inventory import router as inventory_router
from handlers.profile import router as profile_router
from handlers.skills import router as skills_router
from handlers.equipment import router as equipment_router
from handlers.quest import router as quest_router
from handlers.shop import router as shop_router
from handlers.fan_art import router as fan_art_router
from handlers.fan_art_admin import router as fan_art_admin_router
from handlers.fan_art_hunt import router as fan_art_hunt_router, fan_art_scheduler
from handlers.combat import router as combat_router
from handlers.adventure import router as adventure_router
from handlers.pvp import router as pvp_router
from handlers.party import router as party_router
from handlers.membership_requests import router as membership_requests_router
from handlers.social_systems import router as social_systems_router
from handlers.dungeon_expedition import router as dungeon_expedition_router
from handlers.guild import router as guild_router
from handlers.advanced_world import router as advanced_world_router
from handlers.group_boss import router as group_boss_router, boss_scheduler
from handlers.group_link import router as group_link_router
from services.pet_training_service import pet_training_scheduler
from services.death_service import death_revival_scheduler
from services.dungeon_expedition_service import dungeon_scheduler
from middlewares.group_boss_registration import GroupBossRegistrationMiddleware
from services.scheduler_leader import run_schedulers_as_leader


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("world_eldoria")
dp = Dispatcher()
dp.update.middleware(UpdateTimingMiddleware())


@dp.errors()
async def log_unhandled_update_error(event: ErrorEvent) -> bool:
    """Log unexpected handler failures and give callback users feedback."""
    update = event.update
    exception = event.exception
    logger.error(
        "Unhandled update error (update_id=%s): %r",
        getattr(update, "update_id", None),
        exception,
        exc_info=(type(exception), exception, exception.__traceback__),
    )

    callback = getattr(update, "callback_query", None)
    if callback is not None:
        try:
            await callback.answer(
                "❌ این بخش با خطا روبه‌رو شد. خطای کامل در ترمینال ربات ثبت شده است.",
                show_alert=True,
            )
        except Exception:
            pass
    return True


username_sync = UsernameSyncMiddleware()
panel_owner = PanelOwnerMiddleware()

dp.message.outer_middleware(CharacterRequiredMiddleware())
dp.callback_query.outer_middleware(CharacterRequiredMiddleware())
dp.callback_query.outer_middleware(DeleteMainMenuOnClickMiddleware())
dp.callback_query.outer_middleware(AdventureFightLockMiddleware())
dp.message.outer_middleware(GuardianMiddleware())
dp.message.middleware(username_sync)
dp.message.middleware(GroupBossRegistrationMiddleware())
dp.callback_query.outer_middleware(panel_owner)
dp.callback_query.middleware(username_sync)

dp.include_router(guardian_router)
dp.include_router(start_router)
dp.include_router(character_creation_router)
dp.include_router(race_router)
dp.include_router(element_router)

# پنل ادمین و گیفت فن‌آرت
dp.include_router(admin_temp_router)
dp.include_router(admin_premium_emoji_router)
dp.include_router(admin_resource_gifts_router)
dp.include_router(fan_art_gifts_router)

dp.include_router(group_boss_router)
dp.include_router(group_link_router)
# Register marketplace FSM handlers before general menu/text routers so
# active market input always reaches its state-specific handler.
dp.include_router(advanced_world_router)
dp.include_router(command_aliases_router)
dp.include_router(main_menu_router)
dp.include_router(shop_router)
dp.include_router(inventory_router)
dp.include_router(profile_router)
dp.include_router(skills_router)
dp.include_router(equipment_router)
dp.include_router(quest_router)
dp.include_router(fan_art_admin_router)
dp.include_router(fan_art_router)
dp.include_router(fan_art_hunt_router)
dp.include_router(combat_router)
dp.include_router(adventure_router)
dp.include_router(pvp_router)
dp.include_router(membership_requests_router)
dp.include_router(party_router)
dp.include_router(social_systems_router)
dp.include_router(dungeon_expedition_router)
dp.include_router(guild_router)


async def setup_bot_commands() -> None:
    # Keep the same public command list in private chats and groups so Telegram can
    # suggest the same commands wherever the bot is used. Admin authorization is
    # still enforced by the handlers themselves.
    commands = [
        BotCommand(command="start", description="شروع بازی / ساخت شخصیت"),
        BotCommand(command="menu", description="باز کردن منوی اصلی"),
        BotCommand(command="guide", description="راهنمای دنیای فانتزی اِلدوریا"),
        BotCommand(command="arts", description="تالار فن‌آرت اِلدوریا"),
        BotCommand(command="profile", description="نمایش پروفایل قهرمان"),
        BotCommand(command="sandoghche", description="صندوقچه"),
        BotCommand(command="skills", description="مهارت‌ها"),
        BotCommand(command="tajhizat", description="تجهیزات"),
        BotCommand(command="mamoriah", description="مأموریت‌ها"),
        BotCommand(command="majarajoyi", description="ماجراجویی"),
        BotCommand(command="crafting", description="کرفتینگ"),
        BotCommand(command="pet", description="پت"),
        BotCommand(command="event", description="ایونت‌ها"),
        BotCommand(command="parti", description="پارتی"),
        BotCommand(command="guild", description="گیلد"),
        BotCommand(command="player_shop", description="بازار بازیکنان"),
        BotCommand(command="ahangari", description="آهنگری"),
        BotCommand(command="help", description="راهنما"),
        BotCommand(command="change", description="تبدیل گلد به جم"),
        BotCommand(command="setting", description="تنظیمات"),
        BotCommand(command="shop", description="فروشگاه اِلدوریا"),
        BotCommand(command="mypet", description="اطلاعات پت و سهمیه حمله"),
        BotCommand(command="pvp", description="حمله مستقیم به بازیکن با ریپلای"),
        BotCommand(command="bounty", description="تابلوی جایزه"),
        BotCommand(command="attack", description="حمله به باس فعال گروه"),
        BotCommand(command="magic", description="انتخاب جادو برای باس"),
        BotCommand(command="heal", description="استفاده از معجون سلامتی"),
        BotCommand(command="mana", description="ریکاوری مانا با معجون"),
        BotCommand(command="art", description="فن‌آرت با ریپلای روی تصویر"),
        BotCommand(command="boss_status", description="وضعیت باس گروه"),
        BotCommand(command="dungeon", description="غنیمت‌های دانجن"),
        BotCommand(command="market_items", description="فهرست آیتم‌های بازار"),
        BotCommand(command="market_sell", description="فروش آیتم در بازار"),
        BotCommand(command="market_equipment", description="فهرست تجهیزات بازار"),
        BotCommand(command="market_sell_equipment", description="فروش تجهیزات در بازار"),
        BotCommand(command="market_equipment_items", description="فهرست شناسه تجهیزات"),
        BotCommand(command="fanart_add", description="افزودن فن‌آرت (مجازها)"),
        BotCommand(command="cancel", description="لغو عملیات جاری"),
        BotCommand(command="myid", description="نمایش شناسه تلگرام"),
        BotCommand(command="remove_boss", description="حذف باس فعال (فقط ادمین)"),
        BotCommand(command="admin", description="پنل مدیریت بازی (فقط ادمین)"),
        BotCommand(command="gap", description="پنل مدیریت گروه"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    await bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())


async def repair_command_like_character_names() -> int:
    """Repair legacy character names that were accidentally saved as Telegram commands."""
    repaired = 0
    async with AsyncSessionLocal() as session:
        rows = (await session.scalars(
            select(Character).where(
                (Character.name.like("/%")) | (Character.name.like("!%"))
            )
        )).all()
        existing_names = set((await session.scalars(select(Character.name))).all())
        for character in rows:
            existing_names.discard(character.name)
            username = (character.telegram_username or "").strip().lstrip("@")
            candidate = username if username and not username.startswith(("/", "!")) else ""
            if not candidate or candidate in existing_names:
                candidate = f"قهرمان-{character.telegram_id}"
            candidate = candidate[:32]
            base = candidate
            suffix = 2
            while candidate in existing_names:
                tail = f"-{suffix}"
                candidate = f"{base[:32-len(tail)]}{tail}"
                suffix += 1
            character.name = candidate
            existing_names.add(candidate)
            repaired += 1
        if repaired:
            await session.commit()
    if repaired:
        logger.warning("Repaired %s legacy character names that looked like commands.", repaired)
    return repaired


async def main() -> None:
    logger.info("World Eldoria is starting...")

    try:
        await repair_command_like_character_names()
        await setup_bot_commands()
        logger.info("Bot commands registered.")

        scheduler_task = asyncio.create_task(
            run_schedulers_as_leader(
                (
                    boss_scheduler,
                    fan_art_scheduler,
                    lambda: pet_training_scheduler(bot),
                    lambda: death_revival_scheduler(bot),
                    lambda: dungeon_scheduler(bot),
                )
            ),
            name="world-eldoria-scheduler-leader",
        )
        try:
            await dp.start_polling(bot)
        finally:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass

    except asyncio.CancelledError:
        logger.info("World Eldoria polling was cancelled.")
        raise

    except Exception:
        logger.exception(
            "World Eldoria stopped because of an unexpected error."
        )
        raise

    finally:
        logger.info("Closing Telegram bot session...")

        if not bot.session.closed:
            await bot.session.close()

        try:
            await redis.aclose()
        except Exception:
            logger.exception("Failed to close Redis connection pool cleanly.")

        try:
            await engine.dispose()
        except Exception:
            logger.exception("Failed to dispose SQLAlchemy connection pool cleanly.")

        logger.info("World Eldoria stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("World Eldoria stopped by keyboard interrupt.")