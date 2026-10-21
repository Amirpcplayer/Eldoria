from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from database.database import AsyncSessionLocal
from models.character import Character
from models.social_systems import DungeonRun, GroupDungeonEvent, Party, PartyMember


PARTY_CREATION_COSTS = {
    4: 5000,
    6: 7000,
    8: 9000,
    10: 11000,
}

PARTY_UPGRADE_COST = 2000
PARTY_MAX_CAPACITY = 10
PARTY_MIN_CAPACITY = 4
PARTY_NAME_MAX_LENGTH = 40
PARTY_TITLE_MAX_LENGTH = 40
PARTY_DESCRIPTION_MAX_LENGTH = 500


async def _get_active_member(
    session,
    telegram_id: int,
) -> PartyMember | None:
    return await session.scalar(
        select(PartyMember)
        .join(Party, Party.id == PartyMember.party_id)
        .where(
            PartyMember.telegram_id == telegram_id,
            Party.status == "open",
        )
        .limit(1)
    )


async def get_character_gold(telegram_id: int) -> int | None:
    async with AsyncSessionLocal() as session:
        player = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if player is None:
            return None

        return int(player.gold or 0)


async def get_character_by_username(username: str) -> dict | None:
    normalized = username.strip().lstrip("@").lower()

    if not normalized:
        return None

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                func.lower(Character.telegram_username) == normalized
            )
        )

        if character is None:
            return None

        return {
            "telegram_id": int(character.telegram_id),
            "username": character.telegram_username,
            "name": character.name,
            "level": character.level or 1,
        }


async def get_party_by_id(party_id: int) -> dict | None:
    async with AsyncSessionLocal() as session:
        party = await session.scalar(
            select(Party).where(Party.id == party_id)
        )

        if party is None:
            return None

        count = await session.scalar(
            select(func.count())
            .select_from(PartyMember)
            .where(PartyMember.party_id == party.id)
        )

        return {
            "id": party.id,
            "name": party.name,
            "title": party.title,
            "description": party.description,
            "leader_telegram_id": int(party.leader_telegram_id),
            "max_members": int(party.max_members),
            "member_count": int(count or 0),
            "status": party.status,
        }


async def get_party(telegram_id: int) -> Party | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Party)
            .join(PartyMember, PartyMember.party_id == Party.id)
            .where(
                PartyMember.telegram_id == telegram_id,
                Party.status == "open",
            )
            .limit(1)
        )


async def get_party_members(party_id: int) -> list[dict]:
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(
                PartyMember.telegram_id,
                PartyMember.joined_at,
                Character.name,
                Character.level,
                Character.telegram_username,
            )
            .outerjoin(
                Character,
                Character.telegram_id == PartyMember.telegram_id,
            )
            .join(Party, Party.id == PartyMember.party_id)
            .where(
                PartyMember.party_id == party_id,
                Party.status == "open",
            )
            .order_by(PartyMember.joined_at, PartyMember.id)
        )

        return [
            {
                "telegram_id": int(row.telegram_id),
                "name": row.name or "بازیکن",
                "level": row.level or 1,
                "username": row.telegram_username,
            }
            for row in rows.all()
        ]


async def get_party_details(telegram_id: int) -> dict | None:
    async with AsyncSessionLocal() as session:
        party = await session.scalar(
            select(Party)
            .join(PartyMember, PartyMember.party_id == Party.id)
            .where(
                PartyMember.telegram_id == telegram_id,
                Party.status == "open",
            )
            .limit(1)
        )

        if party is None:
            return None

        count = await session.scalar(
            select(func.count())
            .select_from(PartyMember)
            .where(PartyMember.party_id == party.id)
        )

        return {
            "id": party.id,
            "name": party.name,
            "title": party.title,
            "description": party.description,
            "leader_telegram_id": int(party.leader_telegram_id),
            "max_members": int(party.max_members),
            "member_count": int(count or 0),
            "status": party.status,
        }


async def create_party(
    telegram_id: int,
    name: str,
    title: str,
    description: str,
    capacity: int,
) -> tuple[bool, str, int | None]:
    name = name.strip()
    title = title.strip()
    description = description.strip()

    if capacity not in PARTY_CREATION_COSTS:
        return False, "ظرفیت انتخاب‌شده معتبر نیست.", None

    if not name or len(name) > PARTY_NAME_MAX_LENGTH:
        return False, "نام پارتی باید بین ۱ تا ۴۰ نویسه باشد.", None

    if not title or len(title) > PARTY_TITLE_MAX_LENGTH:
        return False, "عنوان پارتی باید بین ۱ تا ۴۰ نویسه باشد.", None

    # توضیحات خالی مجاز است.
    if len(description) > PARTY_DESCRIPTION_MAX_LENGTH:
        return False, "توضیحات نمی‌تواند بیشتر از ۵۰۰ نویسه باشد.", None

    cost = PARTY_CREATION_COSTS[capacity]

    async with AsyncSessionLocal() as session:
        try:
            # قفل ردیف بازیکن برای جلوگیری از خرج هم‌زمان موجودی.
            player = await session.scalar(
                select(Character)
                .where(Character.telegram_id == telegram_id)
                .with_for_update()
            )

            if player is None:
                return False, "ابتدا شخصیت بازی خود را بساز.", None

            current_member = await _get_active_member(
                session,
                telegram_id,
            )

            if current_member is not None:
                return False, "قبلاً عضو یک پارتی هستی.", None

            current_gold = int(player.gold or 0)

            if current_gold < cost:
                return (
                    False,
                    f"طلای کافی نداری. هزینهٔ ساخت این پارتی "
                    f"{cost:,} طلاست؛ موجودی فعلی: "
                    f"{current_gold:,} طلا.",
                    None,
                )

            party = Party(
                leader_telegram_id=telegram_id,
                name=name,
                title=title,
                description=description,
                max_members=capacity,
                status="open",
            )

            session.add(party)
            await session.flush()

            session.add(
                PartyMember(
                    party_id=party.id,
                    telegram_id=telegram_id,
                )
            )

            # کسر طلا و ساخت پارتی در یک تراکنش هستند.
            player.gold = current_gold - cost

            await session.commit()

            return (
                True,
                f"پارتی ساخته شد؛ {cost:,} طلا پرداخت شد.",
                int(party.id),
            )

        except IntegrityError:
            await session.rollback()
            return False, "ساخت پارتی انجام نشد؛ دوباره تلاش کن.", None

        except Exception:
            await session.rollback()
            raise


async def join_party(
    telegram_id: int,
    party_id: int,
) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        try:
            player = await session.scalar(
                select(Character)
                .where(Character.telegram_id == telegram_id)
                .with_for_update()
            )

            if player is None:
                return False, "ابتدا شخصیت بازی خود را بساز."

            if await _get_active_member(session, telegram_id):
                return False, "ابتدا از پارتی فعلی خارج شو."

            party = await session.scalar(
                select(Party)
                .where(
                    Party.id == party_id,
                    Party.status == "open",
                )
                .with_for_update()
            )

            if party is None:
                return False, "پارتی موردنظر پیدا نشد یا بسته شده است."

            active_dungeon = await session.scalar(
                select(GroupDungeonEvent.id).where(
                    GroupDungeonEvent.party_id == party.id,
                    GroupDungeonEvent.status.in_(["forming", "running"]),
                ).limit(1)
            )
            if active_dungeon is not None:
                return False, "در زمان اجرای دانجن، عضو جدید نمی‌تواند به پارتی ملحق شود."

            count = await session.scalar(
                select(func.count())
                .select_from(PartyMember)
                .where(PartyMember.party_id == party.id)
            )

            active_dungeon = await session.scalar(
                select(GroupDungeonEvent.id).where(
                    GroupDungeonEvent.party_id == party.id,
                    GroupDungeonEvent.status.in_(["forming", "running"]),
                ).limit(1)
            )
            if active_dungeon is not None:
                return False, "در زمان اجرای دانجن، عضو جدید نمی‌تواند به پارتی ملحق شود."

            if (count or 0) >= party.max_members:
                return False, "ظرفیت پارتی تکمیل شده است."

            session.add(
                PartyMember(
                    party_id=party.id,
                    telegram_id=telegram_id,
                )
            )

            await session.commit()

            return True, f"به پارتی «{party.name}» پیوستی."

        except IntegrityError:
            await session.rollback()
            return False, "عضویت انجام نشد؛ ممکن است قبلاً عضو شده باشی."

        except Exception:
            await session.rollback()
            raise


async def join_party_from_invitation(
    telegram_id: int,
    party_id: int,
    inviter_telegram_id: int,
) -> tuple[bool, str]:
    """پذیرش دعوت فقط در صورت فعال بودن پارتی و رهبر بودن دعوت‌کننده."""

    async with AsyncSessionLocal() as session:
        try:
            player = await session.scalar(
                select(Character)
                .where(Character.telegram_id == telegram_id)
                .with_for_update()
            )

            if player is None:
                return False, "ابتدا شخصیت بازی خود را بساز."

            if await _get_active_member(session, telegram_id):
                return False, "ابتدا از پارتی فعلی خارج شو."

            party = await session.scalar(
                select(Party)
                .where(
                    Party.id == party_id,
                    Party.status == "open",
                )
                .with_for_update()
            )

            if party is None:
                return False, "این پارتی بسته شده یا دیگر وجود ندارد."

            if int(party.leader_telegram_id) != inviter_telegram_id:
                return False, "دعوت دیگر معتبر نیست؛ رهبر پارتی تغییر کرده است."

            count = await session.scalar(
                select(func.count())
                .select_from(PartyMember)
                .where(PartyMember.party_id == party.id)
            )

            if (count or 0) >= party.max_members:
                return False, "ظرفیت پارتی تکمیل شده است."

            session.add(
                PartyMember(
                    party_id=party.id,
                    telegram_id=telegram_id,
                )
            )

            await session.commit()

            return True, f"با موفقیت به پارتی «{party.name}» پیوستی."

        except IntegrityError:
            await session.rollback()
            return False, "عضویت انجام نشد؛ ممکن است قبلاً عضو شده باشی."

        except Exception:
            await session.rollback()
            raise


async def leave_party(telegram_id: int) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        member = await _get_active_member(session, telegram_id)

        if member is None:
            return False, "عضو هیچ پارتی نیستی."

        party = await session.scalar(
            select(Party)
            .where(Party.id == member.party_id)
            .with_for_update()
        )

        if party is None:
            await session.delete(member)
            await session.commit()
            return True, "از پارتی خارج شدی."

        dungeon_locked = await session.scalar(
            select(GroupDungeonEvent.id).where(
                GroupDungeonEvent.party_id == party.id,
                GroupDungeonEvent.status.in_(["forming", "running"]),
            ).limit(1)
        )
        if dungeon_locked is not None:
            return False, "تا پایان اکتشاف دانجن نمی‌توانی از پارتی خارج شوی."

        was_leader = int(party.leader_telegram_id) == telegram_id
        party_id = int(party.id)
        await session.delete(member)
        await session.flush()

        if was_leader:
            successor = await session.scalar(
                select(PartyMember)
                .where(PartyMember.party_id == party_id)
                .order_by(PartyMember.joined_at.asc(), PartyMember.id.asc())
                .limit(1)
                .with_for_update()
            )
            if successor is None:
                party.status = "closed"
                await session.commit()
                return True, "از پارتی خارج شدی؛ چون عضو دیگری باقی نمانده بود، پارتی بسته شد."
            party.leader_telegram_id = int(successor.telegram_id)
            await session.commit()
            return True, f"از پارتی خارج شدی؛ رهبری به عضو قدیمی‌تر (شناسهٔ {successor.telegram_id}) منتقل شد."

        await session.commit()
        return True, "از پارتی خارج شدی."


async def rename_party(
    telegram_id: int,
    new_name: str,
) -> tuple[bool, str]:
    new_name = new_name.strip()

    if not new_name or len(new_name) > PARTY_NAME_MAX_LENGTH:
        return False, "نام پارتی باید بین ۱ تا ۴۰ نویسه باشد."

    async with AsyncSessionLocal() as session:
        party = await session.scalar(
            select(Party)
            .where(
                Party.leader_telegram_id == telegram_id,
                Party.status == "open",
            )
            .with_for_update()
        )

        if party is None:
            return False, "فقط رهبر یک پارتی فعال می‌تواند نام را تغییر دهد."

        party.name = new_name
        await session.commit()

        return True, "نام پارتی با موفقیت تغییر کرد."


async def upgrade_party(
    telegram_id: int,
) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        try:
            party = await session.scalar(
                select(Party)
                .where(
                    Party.leader_telegram_id == telegram_id,
                    Party.status == "open",
                )
                .with_for_update()
            )

            if party is None:
                return False, "فقط رهبر پارتی می‌تواند ظرفیت را ارتقا دهد."

            if party.max_members >= PARTY_MAX_CAPACITY:
                return False, "ظرفیت پارتی به حداکثر ۱۰ نفر رسیده است."

            player = await session.scalar(
                select(Character)
                .where(Character.telegram_id == telegram_id)
                .with_for_update()
            )

            if player is None:
                return False, "شخصیت بازی پیدا نشد."

            current_gold = int(player.gold or 0)

            if current_gold < PARTY_UPGRADE_COST:
                return False, "برای ارتقا به ۲٬۰۰۰ طلا نیاز داری."

            old_capacity = int(party.max_members)
            new_capacity = min(old_capacity + 2, PARTY_MAX_CAPACITY)

            player.gold = current_gold - PARTY_UPGRADE_COST
            party.max_members = new_capacity

            await session.commit()

            return (
                True,
                f"ظرفیت پارتی از {old_capacity} به {new_capacity} نفر رسید؛ "
                "۲٬۰۰۰ طلا پرداخت شد.",
            )

        except Exception:
            await session.rollback()
            raise


async def kick_party_member(
    leader_telegram_id: int,
    target_telegram_id: int,
) -> tuple[bool, str, str | None]:
    async with AsyncSessionLocal() as session:
        party = await session.scalar(
            select(Party)
            .where(
                Party.leader_telegram_id == leader_telegram_id,
                Party.status == "open",
            )
            .with_for_update()
        )

        if party is None:
            return False, "پارتی فعالی تحت رهبری تو پیدا نشد.", None

        dungeon_locked = await session.scalar(
            select(GroupDungeonEvent.id).where(
                GroupDungeonEvent.party_id == party.id,
                GroupDungeonEvent.status.in_(["forming", "running"]),
            ).limit(1)
        )
        if dungeon_locked is not None:
            return False, "تا پایان اکتشاف دانجن نمی‌توانی عضوی را از پارتی اخراج کنی.", None

        if target_telegram_id == leader_telegram_id:
            return False, "رهبر نمی‌تواند خودش را اخراج کند.", None

        member = await session.scalar(
            select(PartyMember)
            .where(
                PartyMember.party_id == party.id,
                PartyMember.telegram_id == target_telegram_id,
            )
            .with_for_update()
        )

        if member is None:
            return False, "این بازیکن دیگر عضو پارتی نیست.", None

        party_name = party.name

        await session.delete(member)
        await session.commit()

        return True, "بازیکن از پارتی اخراج شد.", party_name


async def start_party_dungeon(
    telegram_id: int,
    dungeon_key: str = "eldoria_ruins",
) -> tuple[bool, str]:
    if not dungeon_key or len(dungeon_key) > 32:
        return False, "شناسهٔ دانجن معتبر نیست."

    async with AsyncSessionLocal() as session:
        party = await session.scalar(
            select(Party)
            .join(PartyMember, PartyMember.party_id == Party.id)
            .where(
                PartyMember.telegram_id == telegram_id,
                Party.status == "open",
            )
            .with_for_update()
            .limit(1)
        )

        if party is None:
            return False, "برای ورود به دانجن باید عضو یک پارتی باشی."

        if int(party.leader_telegram_id) != telegram_id:
            return False, "فقط رهبر پارتی می‌تواند ورود به دانجن را آغاز کند."

        members = list(
            (
                await session.scalars(
                    select(PartyMember.telegram_id)
                    .where(PartyMember.party_id == party.id)
                    .order_by(PartyMember.joined_at, PartyMember.id)
                )
            ).all()
        )

        if not members:
            return False, "پارتی عضو فعالی ندارد."

        characters = list(
            (
                await session.scalars(
                    select(Character).where(
                        Character.telegram_id.in_(members)
                    )
                )
            ).all()
        )

        if len(characters) != len(members):
            return False, "تمام اعضای پارتی باید شخصیت بازی داشته باشند."

        active_run = await session.scalar(
            select(DungeonRun.id)
            .where(
                DungeonRun.telegram_id.in_(members),
                DungeonRun.status == "active",
            )
            .limit(1)
        )

        if active_run is not None:
            return False, "حداقل یکی از اعضا در حال حاضر دانجن فعالی دارد."

        try:
            for member_id in members:
                session.add(
                    DungeonRun(
                        telegram_id=member_id,
                        party_id=party.id,
                        dungeon_key=dungeon_key,
                        floor=1,
                        status="active",
                        reward_gold=0,
                    )
                )

            await session.commit()

        except IntegrityError:
            await session.rollback()
            return False, "شروع دانجن انجام نشد؛ دوباره تلاش کن."

        except Exception:
            await session.rollback()
            raise

        return (
            True,
            f"پارتی «{party.name}» با {len(members)} عضو وارد دانجن شد.",
        )