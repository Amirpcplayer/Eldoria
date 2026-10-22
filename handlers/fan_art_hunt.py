from __future__ import annotations

import asyncio
import html
import logging
import random
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from bot.bot import bot
from database.database import AsyncSessionLocal
from models.character import Character
from models.fan_art import FanArt, FanArtOwnership, GroupFanArtSpawn
from models.world_systems import GroupBoss
from services.language_service import get_language

router = Router()
logger = logging.getLogger(__name__)
SPAWN_INTERVAL = timedelta(hours=24)

RARITY = {
    "common": {"fa": "معمولی", "en": "Common", "ru": "Обычная"},
    "rare": {"fa": "کمیاب", "en": "Rare", "ru": "Редкая"},
    "epic": {"fa": "حماسی", "en": "Epic", "ru": "Эпическая"},
    "legendary": {"fa": "افسانه‌ای", "en": "Legendary", "ru": "Легендарная"},
    "mythic": {"fa": "اسطوره‌ای", "en": "Mythic", "ru": "Мифическая"},
}

TEXT = {
    "fa": {
        "group_unregistered": "این گروه هنوز در سیستم بازی ثبت نشده است؛ ابتدا یک پیام در گروه بفرستید.",
        "cooldown": "هنوز ۲۴ ساعت از شکار قبلی این گروه نگذشته است.",
        "no_art": "هیچ فن‌آرت فعالی در مجموعه ثبت نشده است.",
        "caption": "🎨 <b>شکار فن‌آرت اِلدوریا!</b>\n\n<b>{name}</b>\n{description}\n\n💎 کمیابی: <b>{rarity}</b>\n💰 ارزش اقتصادی بازی: <b>{value:,} طلا</b>\n\n🏹 برای دریافت، روی همین عکس ریپلای کن و دستور <code>/art</code> را بفرست.\n⚡ فقط اولین دریافت معتبر برنده می‌شود!",
        "send_failed": "ارسال تصویر ناموفق شد؛ دسترسی ربات به گروه و معتبر بودن تصویر را بررسی کن.",
        "spawned": "فن‌آرت «{name}» در گروه ارسال شد.",
        "private": "🎨 دستور /art را در پاسخ به عکس فن‌آرت داخل گروه بفرست.",
        "reply": "❌ باید روی پیام عکس فن‌آرت ریپلای کنی و /art بفرستی.",
        "not_active": "❌ این پیام، فن‌آرت فعال برای شکار نیست.",
        "claimed": "🏁 این فن‌آرت قبلاً دریافت شده است.",
        "unavailable": "❌ این فن‌آرت دیگر در دسترس نیست.",
        "need_character": "❌ ابتدا در ربات با /start شخصیت خود را بساز.",
        "already_owned": "🎨 این فن‌آرت را از قبل داری؛ بازیکن دیگری می‌تواند آن را دریافت کند.",
        "duplicate": "🎨 این فن‌آرت را همین حالا در مجموعه‌ات ثبت کرده‌ای؛ دریافت دوباره ممکن نیست.",
        "winner": "🏆 <b>{user}</b> اولین شکارچی معتبر بود!\n🎨 فن‌آرت «{name}» به مجموعه شخصی او اضافه شد.\nبرای استفاده در پروفایل، از بخش فن‌آرت‌ها آن را فعال کن.",
    },
    "en": {
        "group_unregistered": "This group is not registered in the game yet. Send a message in the group first.",
        "cooldown": "The group must wait 24 hours between fan-art hunts.",
        "no_art": "There are no active fan-art entries in the collection.",
        "caption": "🎨 <b>Eldoria Fan-Art Hunt!</b>\n\n<b>{name}</b>\n{description}\n\n💎 Rarity: <b>{rarity}</b>\n💰 In-game value: <b>{value:,} Gold</b>\n\n🏹 To claim it, reply to this photo with <code>/art</code>.\n⚡ The first valid claim wins!",
        "send_failed": "Could not send the image. Check the bot's group permissions and whether the image is valid.",
        "spawned": "Fan art “{name}” was posted in the group.",
        "private": "🎨 Use /art as a reply to a fan-art photo in a group.",
        "reply": "❌ Reply to the fan-art photo with /art to claim it.",
        "not_active": "❌ This message is not the active fan-art hunt.",
        "claimed": "🏁 This fan art has already been claimed.",
        "unavailable": "❌ This fan art is no longer available.",
        "need_character": "❌ Create your character in the bot first with /start.",
        "already_owned": "🎨 You already own this fan art; another player can claim it.",
        "duplicate": "🎨 This fan art is already in your collection. It cannot be claimed twice.",
        "winner": "🏆 <b>{user}</b> was the first valid hunter!\n🎨 “{name}” has been added to their collection.\nActivate it in the Fan Art section to use it on your profile.",
    },
    "ru": {
        "group_unregistered": "Эта группа ещё не зарегистрирована в игре. Сначала отправьте в неё сообщение.",
        "cooldown": "Между охотами за фан-артом в группе должно пройти 24 часа.",
        "no_art": "В коллекции нет активного фан-арта.",
        "caption": "🎨 <b>Охота за фан-артом Эльдории!</b>\n\n<b>{name}</b>\n{description}\n\n💎 Редкость: <b>{rarity}</b>\n💰 Игровая стоимость: <b>{value:,} золота</b>\n\n🏹 Чтобы получить, ответь на это фото командой <code>/art</code>.\n⚡ Побеждает первый корректный запрос!",
        "send_failed": "Не удалось отправить изображение. Проверь права бота в группе и корректность изображения.",
        "spawned": "Фан-арт «{name}» опубликован в группе.",
        "private": "🎨 Отправь /art ответом на фото фан-арта в группе.",
        "reply": "❌ Чтобы получить фан-арт, ответь на его фото командой /art.",
        "not_active": "❌ Это сообщение не относится к активной охоте за фан-артом.",
        "claimed": "🏁 Этот фан-арт уже получен.",
        "unavailable": "❌ Этот фан-арт больше недоступен.",
        "need_character": "❌ Сначала создай персонажа в боте командой /start.",
        "already_owned": "🎨 Этот фан-арт уже у тебя; его может получить другой игрок.",
        "duplicate": "🎨 Этот фан-арт уже есть в твоей коллекции. Повторное получение невозможно.",
        "winner": "🏆 <b>{user}</b> первым выполнил условия охоты!\n🎨 Фан-арт «{name}» добавлен в его коллекцию.\nАктивируй его в разделе фан-арта, чтобы показывать в профиле.",
    },
}

def _lang(language: str | None) -> str:
    return language if language in TEXT else "fa"

async def spawn_fan_art(chat_id: int, force: bool = False) -> tuple[bool, str]:
    """Spawn a random active art; group announcements use Persian as the neutral default."""
    language = "fa"
    t = TEXT[language]
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        group = await session.scalar(select(GroupBoss).where(GroupBoss.chat_id == chat_id))
        if group is None:
            return False, t["group_unregistered"]
        slot = await session.scalar(select(GroupFanArtSpawn).where(GroupFanArtSpawn.chat_id == chat_id).with_for_update())
        if slot and slot.spawned_at and now - slot.spawned_at < SPAWN_INTERVAL and not force:
            return False, t["cooldown"]
        arts = list((await session.scalars(select(FanArt).where(FanArt.is_active.is_(True)).order_by(FanArt.id))).all())
        if not arts:
            return False, t["no_art"]
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
    caption = t["caption"].format(
        name=html.escape(art_name),
        description=html.escape(description or ""),
        rarity=RARITY.get(rarity, {}).get(language, rarity),
        value=value_gold,
    )
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
        return False, t["send_failed"]
    async with AsyncSessionLocal() as session:
        slot = await session.scalar(select(GroupFanArtSpawn).where(GroupFanArtSpawn.chat_id == chat_id).with_for_update())
        if slot and slot.fan_art_id == art.id and slot.spawned_at == now:
            slot.message_id = sent.message_id
            await session.commit()
    return True, t["spawned"].format(name=art_name)

@router.message(Command("art"))
async def claim_group_fan_art(message: Message):
    language = _lang(await get_language(message.from_user.id)) if message.from_user else "fa"
    t = TEXT[language]
    if not message.chat or message.chat.type not in {"group", "supergroup"}:
        await message.answer(t["private"])
        return
    replied = message.reply_to_message
    if replied is None:
        await message.reply(t["reply"])
        return
    if message.from_user is None or message.from_user.is_bot:
        return
    winner_id = message.from_user.id
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        slot = await session.scalar(select(GroupFanArtSpawn).where(GroupFanArtSpawn.chat_id == message.chat.id).with_for_update())
        if slot is None or slot.message_id != replied.message_id:
            await message.reply(t["not_active"])
            return
        if slot.claimed_by is not None:
            await message.reply(t["claimed"])
            return
        art = await session.scalar(select(FanArt).where(FanArt.id == slot.fan_art_id, FanArt.is_active.is_(True)))
        if art is None:
            await message.reply(t["unavailable"])
            return
        character = await session.scalar(select(Character).where(Character.telegram_id == winner_id))
        if character is None:
            await message.reply(t["need_character"])
            return
        owned = await session.scalar(select(FanArtOwnership.id).where(FanArtOwnership.telegram_id == winner_id, FanArtOwnership.fan_art_id == art.id).limit(1))
        if owned is not None:
            await message.reply(t["already_owned"])
            return
        slot.claimed_by = winner_id
        slot.claimed_at = now
        session.add(FanArtOwnership(telegram_id=winner_id, fan_art_id=art.id, order_id=None, acquired_at=now))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await message.reply(t["duplicate"])
            return
        art_name = art.name
    await message.reply(t["winner"].format(user=html.escape(message.from_user.full_name), name=html.escape(art_name)), parse_mode="HTML")

async def fan_art_scheduler() -> None:
    """Find due group spawns in one query rather than one query per group."""
    while True:
        try:
            now = datetime.utcnow()
            cutoff = now - SPAWN_INTERVAL
            async with AsyncSessionLocal() as session:
                due = list((await session.scalars(
                    select(GroupBoss.chat_id)
                    .outerjoin(GroupFanArtSpawn, GroupFanArtSpawn.chat_id == GroupBoss.chat_id)
                    .where(or_(
                        GroupFanArtSpawn.id.is_(None),
                        GroupFanArtSpawn.spawned_at.is_(None),
                        GroupFanArtSpawn.spawned_at <= cutoff,
                    ))
                    .order_by(GroupFanArtSpawn.spawned_at.asc().nullsfirst(), GroupBoss.chat_id)
                    .limit(100)
                )).all())
            for chat_id in due:
                await spawn_fan_art(chat_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Fan-art scheduler iteration failed")
        await asyncio.sleep(60)
