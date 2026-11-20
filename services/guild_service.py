from __future__ import annotations
from utils.clock import utcnow_naive

import re
from datetime import datetime
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from utils.group_name_uniqueness import reserve_name_check
from database.database import AsyncSessionLocal
from models.character import Character
from models.social_systems import Guild, GuildMember

GUILD_NAME_MAX = 40
GUILD_TAG_MAX = 8
GUILD_START_CAPACITY = 30
GUILD_DONATION_MIN = 100
GUILD_MAX_LEVEL = 100
GUILD_CREATION_GOLD_COST = 50_000
GUILD_CREATION_GEM_COST = 10
GUILD_LEADER_REWARD_GOLD = 1_000
GUILD_LEADER_REWARD_SECONDS = 24 * 60 * 60


def _clean_name(name: str) -> str:
    return " ".join((name or "").split()).strip()


def _clean_tag(tag: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", (tag or "").strip()).upper()


async def _locked_membership(session, telegram_id: int):
    """Caller locks Character first; all membership writers lock Guild before Member."""
    guild_id = await session.scalar(
        select(GuildMember.guild_id).where(GuildMember.telegram_id == telegram_id).limit(1)
    )
    if guild_id is None:
        return None, None
    guild = await session.scalar(select(Guild).where(Guild.id == guild_id).with_for_update())
    member = await session.scalar(select(GuildMember).where(
        GuildMember.telegram_id == telegram_id, GuildMember.guild_id == guild_id
    ).with_for_update())
    return guild, member


async def get_guild_for_player(telegram_id: int) -> dict | None:
    async with AsyncSessionLocal() as session:
        await session.scalar(select(Character.id).where(
            Character.telegram_id == telegram_id
        ).with_for_update())
        guild, member = await _locked_membership(session, telegram_id)
        if member is None:
            # Serialize repair with join/create and with guild deletion/transfer.
            guild = await session.scalar(select(Guild).where(
                Guild.owner_telegram_id == telegram_id
            ).limit(1).with_for_update())
            if guild is None:
                return None
            member = GuildMember(guild_id=guild.id, telegram_id=telegram_id, role="owner")
            session.add(member)
            await session.flush()
        if guild is None:
            return None
        count = await session.scalar(
            select(func.count(GuildMember.id)).where(GuildMember.guild_id == guild.id)
        ) or 0
        result = {
            "id": guild.id, "name": guild.name, "tag": guild.tag,
            "owner_telegram_id": guild.owner_telegram_id,
            "max_members": guild.max_members, "level": guild.level,
            "xp": guild.xp, "treasury_gold": int(guild.treasury_gold or 0), "description": guild.description, "motto": guild.motto, "emblem": guild.emblem, "member_count": int(count),
            "role": member.role, "created_at": guild.created_at,
            "next_level_xp": _next_level_xp(guild.level),
        }
        await session.commit()
        return result


def _next_level_xp(level: int) -> int:
    return level * 1000


async def create_guild(telegram_id: int, name: str, tag: str) -> tuple[bool, str]:
    name = _clean_name(name)
    tag = _clean_tag(tag)
    if not 2 <= len(name) <= GUILD_NAME_MAX:
        return False, f"نام گیلد باید بین ۲ تا {GUILD_NAME_MAX} نویسه باشد."
    if not 2 <= len(tag) <= GUILD_TAG_MAX:
        return False, f"تگ باید ۲ تا {GUILD_TAG_MAX} حرف یا عدد انگلیسی باشد."
    async with AsyncSessionLocal() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == telegram_id).with_for_update())
        if character is None:
            return False, "ابتدا در بازی شخصیت بساز."
        member = await session.scalar(select(GuildMember.id).where(GuildMember.telegram_id == telegram_id))
        owned = await session.scalar(select(Guild.id).where(Guild.owner_telegram_id == telegram_id).limit(1))
        if member or owned:
            return False, "قبلاً عضو یک گیلد هستی؛ ابتدا از گیلد فعلی خارج شو."
        if int(character.gold or 0) < GUILD_CREATION_GOLD_COST:
            return False, f"برای ساخت گیلد به {GUILD_CREATION_GOLD_COST:,} طلا نیاز داری."
        if int(character.gems or 0) < GUILD_CREATION_GEM_COST:
            return False, f"برای ساخت گیلد به {GUILD_CREATION_GEM_COST} جم نیاز داری."
        try:
            duplicate_name = await reserve_name_check(session, 714002, Guild, name)
        except ValueError:
            return False, "نام گیلد معتبر نیست."
        duplicate_tag = await session.scalar(select(Guild.id).where(func.upper(Guild.tag) == tag).limit(1))
        duplicate = duplicate_name or duplicate_tag
        if duplicate:
            return False, "این نام یا تگ قبلاً ثبت شده است. نام و تگ دیگری انتخاب کن."
        guild = Guild(name=name, tag=tag, owner_telegram_id=telegram_id, max_members=GUILD_START_CAPACITY, level=1, xp=0)
        session.add(guild)
        await session.flush()
        session.add(GuildMember(guild_id=guild.id, telegram_id=telegram_id, role="owner"))
        # Fee and guild creation share one transaction: no fee is lost on failure.
        character.gold = int(character.gold or 0) - GUILD_CREATION_GOLD_COST
        character.gems = int(character.gems or 0) - GUILD_CREATION_GEM_COST
        guild_id = guild.id
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return False, "نام یا تگ گیلد هم‌زمان توسط بازیکن دیگری ثبت شده است؛ دوباره تلاش کن."
        return True, f"گیلد «{name}» با تگ [{tag}] ساخته شد. هزینه: {GUILD_CREATION_GOLD_COST:,} طلا و {GUILD_CREATION_GEM_COST} جم. شناسهٔ گیلد: GLD-{guild_id:04d}"


async def join_guild(telegram_id: int, guild_id: int) -> tuple[bool, str]:
    if type(guild_id) is not int or guild_id <= 0:
        return False, "شناسهٔ گیلد معتبر نیست."
    async with AsyncSessionLocal() as session:
        character = await session.scalar(select(Character.id).where(Character.telegram_id == telegram_id).with_for_update())
        if character is None:
            return False, "ابتدا شخصیت بساز."
        current = await session.scalar(select(GuildMember.id).where(GuildMember.telegram_id == telegram_id))
        owned = await session.scalar(select(Guild.id).where(Guild.owner_telegram_id == telegram_id).limit(1))
        if current or owned:
            return False, "هم‌اکنون عضو یک گیلد هستی."
        guild = await session.scalar(select(Guild).where(Guild.id == guild_id).with_for_update())
        if guild is None:
            return False, "گیلدی با این شناسه پیدا نشد."
        count = await session.scalar(select(func.count(GuildMember.id)).where(GuildMember.guild_id == guild_id)) or 0
        if count >= guild.max_members:
            return False, "ظرفیت گیلد تکمیل است."
        session.add(GuildMember(guild_id=guild_id, telegram_id=telegram_id, role="member"))
        name, tag = guild.name, guild.tag
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return False, "عضویت ثبت نشد؛ ممکن است هم‌زمان عضو گیلد دیگری شده باشی."
        return True, f"به گیلد «{name}» [{tag}] پیوستی."


async def guild_members(telegram_id: int) -> tuple[dict | None, list[dict]]:
    async with AsyncSessionLocal() as session:
        row = (await session.execute(select(Guild, GuildMember).join(GuildMember, GuildMember.guild_id == Guild.id).where(GuildMember.telegram_id == telegram_id).limit(1))).first()
        if not row:
            return None, []
        guild, my_membership = row
        results = (await session.execute(
            select(GuildMember, Character.name, Character.level, Character.telegram_username)
            .outerjoin(Character, Character.telegram_id == GuildMember.telegram_id)
            .where(GuildMember.guild_id == guild.id)
            .order_by(GuildMember.role.asc(), GuildMember.joined_at.asc(), GuildMember.id.asc())
        )).all()
        members = [{"telegram_id": int(m.telegram_id), "name": name or "ماجراجو", "level": level or 1, "username": username, "role": m.role, "joined_at": m.joined_at} for m, name, level, username in results]
        count = len(members)
        details = {"id": guild.id, "name": guild.name, "tag": guild.tag, "owner_telegram_id": guild.owner_telegram_id, "max_members": guild.max_members, "level": guild.level, "xp": guild.xp, "member_count": count, "role": my_membership.role, "next_level_xp": _next_level_xp(guild.level)}
        return details, members


async def browse_guilds(limit: int = 10) -> list[dict]:
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Guild).order_by(Guild.level.desc(), Guild.xp.desc(), Guild.created_at.asc()).limit(max(1, min(limit, 20))))).scalars().all()
        output = []
        for guild in rows:
            count = await session.scalar(select(func.count(GuildMember.id)).where(GuildMember.guild_id == guild.id)) or 0
            output.append({"id": guild.id, "name": guild.name, "tag": guild.tag, "level": guild.level, "xp": guild.xp, "member_count": int(count), "max_members": guild.max_members})
        return output


async def donate_guild_gold(telegram_id: int, amount: int) -> tuple[bool, str]:
    if type(amount) is not int or amount < GUILD_DONATION_MIN:
        return False, f"حداقل کمک {GUILD_DONATION_MIN:,} طلا است."
    async with AsyncSessionLocal() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == telegram_id).with_for_update())
        if character is None:
            return False, "شخصیت پیدا نشد."
        guild, membership = await _locked_membership(session, telegram_id)
        if membership is None:
            return False, "برای کمک‌کردن باید عضو گیلد باشی."
        if guild is None:
            return False, "گیلد پیدا نشد."
        if character.gold < amount:
            return False, f"طلای کافی نداری. موجودی: {character.gold:,}"
        if guild.level >= GUILD_MAX_LEVEL:
            return False, "گیلد به بالاترین سطح رسیده است."
        character.gold -= amount
        guild.treasury_gold = int(guild.treasury_gold or 0) + amount
        guild.xp += amount
        gained_levels = 0
        while guild.level < GUILD_MAX_LEVEL and guild.xp >= _next_level_xp(guild.level):
            guild.xp -= _next_level_xp(guild.level)
            guild.level += 1
            gained_levels += 1
            if guild.level % 5 == 0:
                guild.max_members = min(100, guild.max_members + 5)
        level, gold = guild.level, character.gold
        await session.commit()
        level_text = f"\n🎉 گیلد {gained_levels} سطح ارتقا یافت؛ سطح فعلی: {level}." if gained_levels else ""
        return True, f"{amount:,} طلا به خزانهٔ گیلد کمک شد و {amount:,} تجربهٔ گیلد دریافت شد.{level_text}\n💰 موجودی تو: {gold:,} طلا"


async def leave_guild(telegram_id: int, successor_telegram_id: int | None = None) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        await session.scalar(select(Character.id).where(
            Character.telegram_id == telegram_id
        ).with_for_update())
        guild, membership = await _locked_membership(session, telegram_id)
        if membership is None:
            return False, "عضو هیچ گیلدی نیستی."
        if guild is None:
            await session.delete(membership)
            await session.commit()
            return True, "عضویت قدیمی پاک‌سازی شد."
        if guild.owner_telegram_id == telegram_id:
            if successor_telegram_id is not None:
                successor = await session.scalar(select(GuildMember).where(
                    GuildMember.guild_id == guild.id,
                    GuildMember.telegram_id == successor_telegram_id,
                    GuildMember.telegram_id != telegram_id,
                ).with_for_update())
                if successor is None:
                    return False, "عضو انتخاب‌شده دیگر عضو این گیلد نیست."
                successor.role = "owner"
                guild.owner_telegram_id = int(successor.telegram_id)
                successor_id = successor.telegram_id
                await session.delete(membership)
                await session.commit()
                return True, f"از گیلد خارج شدی؛ رهبری به شناسهٔ {successor_id} منتقل شد."
            other_id = await session.scalar(select(GuildMember.id).where(
                GuildMember.guild_id == guild.id,
                GuildMember.telegram_id != telegram_id,
            ).limit(1))
            if other_id is not None:
                return False, "برای خروج رهبر، ابتدا یکی از اعضا را به‌عنوان رهبر جدید انتخاب کن."
            await session.delete(membership)
            await session.delete(guild)
            await session.commit()
            return True, "از گیلد خارج شدی؛ چون تنها عضو بودی، گیلد نیز حذف شد."
        await session.delete(membership)
        await session.commit()
        return True, "با موفقیت از گیلد خارج شدی."


async def disband_guild(telegram_id: int) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        guild = await session.scalar(select(Guild).where(
            Guild.owner_telegram_id == telegram_id
        ).with_for_update())
        if guild is None:
            return False, "فقط رهبر گیلد می‌تواند آن را حذف کند."
        name = guild.name
        await session.execute(delete(GuildMember).where(GuildMember.guild_id == guild.id))
        await session.delete(guild)
        await session.commit()
        return True, f"گیلد «{name}» به‌طور کامل حذف شد."


async def claim_guild_leader_reward(telegram_id: int) -> tuple[bool, str]:
    """Claim 1,000 personal Gold every 24h, only for the current guild leader."""
    from datetime import timedelta

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == telegram_id).with_for_update()
        )
        guild, member = await _locked_membership(session, telegram_id)
        if member is None or member.role != "owner":
            return False, "این پاداش فقط برای رهبر فعلی گیلد است."
        if guild is None or character is None or int(guild.owner_telegram_id) != telegram_id:
            return False, "رهبری گیلد تغییر کرده است؛ این پاداش در دسترس نیست."
        now = utcnow_naive()
        if guild.last_leader_reward_at and now < guild.last_leader_reward_at + timedelta(seconds=GUILD_LEADER_REWARD_SECONDS):
            remaining = int((guild.last_leader_reward_at + timedelta(seconds=GUILD_LEADER_REWARD_SECONDS) - now).total_seconds())
            hours, minutes = divmod(max(0, remaining) // 60, 60)
            return False, f"پاداش روزانه قبلاً دریافت شده؛ {hours} ساعت و {minutes} دقیقه دیگر بازگرد."
        character.gold = int(character.gold or 0) + GUILD_LEADER_REWARD_GOLD
        guild.last_leader_reward_at = now
        await session.commit()
        return True, f"👑 پاداش روزانهٔ رهبری دریافت شد: {GUILD_LEADER_REWARD_GOLD:,} طلا به موجودی شخصی‌ات افزوده شد."


async def get_guild_by_id(guild_id: int) -> dict | None:
    async with AsyncSessionLocal() as session:
        guild = await session.scalar(select(Guild).where(Guild.id == guild_id))
        if guild is None:
            return None
        count = await session.scalar(select(func.count(GuildMember.id)).where(GuildMember.guild_id == guild.id)) or 0
        return {"id": guild.id, "name": guild.name, "tag": guild.tag,
                "owner_telegram_id": int(guild.owner_telegram_id),
                "member_count": int(count), "max_members": int(guild.max_members)}
