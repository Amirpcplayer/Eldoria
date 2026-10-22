from __future__ import annotations

import asyncio
import html
import logging
import random
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from bot.bot import bot
from database.database import AsyncSessionLocal
from models.character import Character
from models.fan_art import FanArt, FanArtOwnership, GroupFanArtSpawn
from models.world_systems import GroupBoss

router = Router()
logger = logging.getLogger(__name__)
SPAWN_INTERVAL = timedelta(hours=24)
RARITY_FA = {"common": "معمولی", "rare": "کمیاب", "epic": "حماسی", "legendary": "افسانه‌ای", "mythic": "اسطوره‌ای"}

async def spawn_fan_art(chat_id: int, force: bool = False) -> tuple[bool, str]:
    """Spawn a random active art; store one independent claim slot per group."""
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        group = await session.scalar(select(GroupBoss).where(GroupBoss.chat_id == chat_id))
        if group is None:
            return False, "این گروه هنوز در سیستم بازی ثبت نشده است؛ ابتدا یک پیام در گروه بفرستید."
        slot = await session.scalar(select(GroupFanArtSpawn).where(GroupFanArtSpawn.chat_id == chat_id).with_for_update())
        if slot and slot.spawned_at and now - slot.spawned_at < SPAWN_INTERVAL and not force:
            return False, "هنوز ۲۴ ساعت از اسپان قبلی این گروه نگذشته است."
        arts = list((await session.scalars(select(FanArt).where(FanArt.is_active.is_(True)).order_by(FanArt.id))).all())
        if not arts:
            return False, "هیچ فن‌آرت فعالی در مجموعه ثبت نشده است."
        art = random.choice(arts)
        if slot is None:
            slot = GroupFanArtSpawn(chat_id=chat_id, fan_art_id=art.id, spawned_at=now, message_id=None, claimed_by=None, claimed_at=None)
            session.add(slot)
        else:
            slot.fan_art_id = art.id
            slot.spawned_at = now
            slot.message_id = None
            slot.claimed_by = None
            slot.claimed_at = None
        await session.commit()
        art_name, description, file_id, rarity, value_gold = art.name, art.description, art.image_file_id, art.rarity, int(art.value_gold or 0)
    caption = (f"🎨 <b>شکار فن‌آرت اِلدوریا!</b>\n\n<b>{html.escape(art_name)}</b>\n{html.escape(description)}\n\n"
               f"💎 کمیابی: <b>{RARITY_FA.get(rarity, rarity)}</b>\n💰 ارزش اقتصادی بازی: <b>{value_gold:,} طلا</b>\n\n"
               "🏹 برای دریافت، روی همین عکس ریپلای کن و دستور <code>/art</code> را بفرست.\n"
               "⚡ فقط اولین دریافت معتبر برنده می‌شود!")
    try:
        sent = await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, parse_mode="HTML")
    except Exception:
        logger.exception("Failed to spawn fan art in chat %s", chat_id)
        async with AsyncSessionLocal() as session:
            slot = await session.scalar(select(GroupFanArtSpawn).where(GroupFanArtSpawn.chat_id == chat_id).with_for_update())
            if slot and slot.spawned_at == now:
                slot.spawned_at = now - SPAWN_INTERVAL
                slot.message_id = None
                await session.commit()
        return False, "ارسال تصویر ناموفق شد؛ دسترسی ربات به گروه و معتبر بودن تصویر را بررسی کن."
    async with AsyncSessionLocal() as session:
        slot = await session.scalar(select(GroupFanArtSpawn).where(GroupFanArtSpawn.chat_id == chat_id).with_for_update())
        if slot and slot.fan_art_id == art.id and slot.spawned_at == now:
            slot.message_id = sent.message_id
            await session.commit()
    return True, f"فن‌آرت «{art_name}» در گروه ارسال شد."

@router.message(Command("art"))
async def claim_group_fan_art(message: Message):
    if not message.chat or message.chat.type not in {"group", "supergroup"}:
        await message.answer("🎨 دستور /art را در پاسخ به عکس فن‌آرت داخل گروه بفرست.")
        return
    replied = message.reply_to_message
    if replied is None:
        await message.reply("❌ باید روی پیام عکس فن‌آرت ریپلای کنی و /art بفرستی.")
        return
    if message.from_user is None or message.from_user.is_bot:
        return
    winner_id = message.from_user.id
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        slot = await session.scalar(select(GroupFanArtSpawn).where(GroupFanArtSpawn.chat_id == message.chat.id).with_for_update())
        if slot is None or slot.message_id != replied.message_id:
            await message.reply("❌ این پیام، فن‌آرت فعال برای شکار نیست.")
            return
        if slot.claimed_by is not None:
            await message.reply("🏁 این فن‌آرت قبلاً دریافت شده است.")
            return
        art = await session.scalar(select(FanArt).where(FanArt.id == slot.fan_art_id, FanArt.is_active.is_(True)))
        if art is None:
            await message.reply("❌ این فن‌آرت دیگر در دسترس نیست.")
            return
        character = await session.scalar(select(Character).where(Character.telegram_id == winner_id))
        if character is None:
            await message.reply("❌ ابتدا در ربات با /start شخصیت خود را بساز.")
            return
        owned = await session.scalar(select(FanArtOwnership.id).where(FanArtOwnership.telegram_id == winner_id, FanArtOwnership.fan_art_id == art.id).limit(1))
        if owned is not None:
            await message.reply("🎨 این فن‌آرت را از قبل داری؛ بازیکن دیگری می‌تواند آن را دریافت کند.")
            return
        slot.claimed_by = winner_id
        slot.claimed_at = now
        session.add(FanArtOwnership(telegram_id=winner_id, fan_art_id=art.id, order_id=None, acquired_at=now))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await message.reply("🎨 این فن‌آرت را همین حالا در مجموعه‌ات ثبت کرده‌ای؛ دریافت دوباره ممکن نیست.")
            return
        art_name = art.name
    name = html.escape(message.from_user.full_name)
    await message.reply(f"🏆 <b>{name}</b> اولین شکارچی معتبر بود!\n🎨 فن‌آرت «{art_name}» به مجموعه شخصی او اضافه شد.\nبرای استفاده در پروفایل، از بخش فن‌آرت‌ها آن را فعال کن.", parse_mode="HTML")

async def fan_art_scheduler() -> None:
    """Find due group spawns in one query rather than one query per group."""
    while True:
        try:
            now = datetime.utcnow()
            cutoff = now - SPAWN_INTERVAL
            async with AsyncSessionLocal() as session:
                due = list((await session.scalars(
                    select(GroupBoss.chat_id)
                    .outerjoin(
                        GroupFanArtSpawn,
                        GroupFanArtSpawn.chat_id == GroupBoss.chat_id,
                    )
                    .where(
                        or_(
                            GroupFanArtSpawn.id.is_(None),
                            GroupFanArtSpawn.spawned_at.is_(None),
                            GroupFanArtSpawn.spawned_at <= cutoff,
                        )
                    )
                )).all())
            for chat_id in due:
                await spawn_fan_art(chat_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Fan-art scheduler iteration failed")
        await asyncio.sleep(60)
