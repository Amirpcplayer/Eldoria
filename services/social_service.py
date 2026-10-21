from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import desc, func, select, update

from database.database import AsyncSessionLocal

from models.character import Character
from models.fan_art import FanArt, FanArtOwnership
from models.social_systems import (
    PlayerSetting,
    Party,
    PartyMember,
    Guild,
    GuildMember,
    DungeonRun,
    PvpChallenge,
    CraftRecipe,
    Pet,
    CharacterPet,
    GameEvent,
)


# ============================================================
# Settings
# ============================================================

async def get_or_create_settings(telegram_id: int):
    async with AsyncSessionLocal() as session:
        obj = await session.scalar(
            select(PlayerSetting).where(
                PlayerSetting.telegram_id == telegram_id
            )
        )

        if obj is None:
            obj = PlayerSetting(telegram_id=telegram_id)
            session.add(obj)
            await session.commit()
            await session.refresh(obj)

        return obj


async def toggle_group_fanart(telegram_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        obj = await session.scalar(
            select(PlayerSetting).where(
                PlayerSetting.telegram_id == telegram_id
            )
        )

        if obj is None:
            obj = PlayerSetting(telegram_id=telegram_id)
            session.add(obj)
            await session.flush()

        obj.show_profile_fan_art_in_groups = (
            not obj.show_profile_fan_art_in_groups
        )

        result = obj.show_profile_fan_art_in_groups
        await session.commit()
        return result


async def get_active_profile_fanart(telegram_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FanArt)
            .join(
                FanArtOwnership,
                FanArtOwnership.fan_art_id == FanArt.id,
            )
            .join(
                Character,
                Character.telegram_id == FanArtOwnership.telegram_id,
            )
            .where(
                Character.telegram_id == telegram_id,
                Character.active_fan_art_id == FanArt.id,
            )
            .limit(1)
        )

        return result.scalar_one_or_none()


async def set_profile_fanart(
    telegram_id: int,
    fan_art_id: int,
) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        player = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if player is None:
            return False, "قهرمان پیدا نشد."

        owned = await session.scalar(
            select(FanArtOwnership.id).where(
                FanArtOwnership.telegram_id == telegram_id,
                FanArtOwnership.fan_art_id == fan_art_id,
            )
        )

        if owned is None:
            return False, "این Fan Art را مالک نیستی."

        player.active_fan_art_id = fan_art_id
        await session.commit()

        return True, "Fan Art پروفایل تغییر کرد."


# ============================================================
# Party
# ============================================================

async def _member_party(telegram_id: int):
    """
    دریافت پارتی بازی که عضو آن است.
    فقط پارتی‌های باز در نظر گرفته می‌شوند.
    """

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Party)
            .join(
                PartyMember,
                PartyMember.party_id == Party.id,
            )
            .where(
                PartyMember.telegram_id == telegram_id,
                Party.status == "open",
            )
            .limit(1)
        )

        return result.scalar_one_or_none()


async def get_party(telegram_id: int):
    """دریافت پارتی فعلی بازیکن."""

    return await _member_party(telegram_id)


async def create_party(
    telegram_id: int,
    name: str = "پارتی اِلدوریا",
) -> tuple[Party | None, str]:
    """
    ساخت پارتی و اضافه‌کردن سازنده به‌عنوان عضو و رهبر.

    بررسی عضویت، ساخت پارتی و افزودن عضو در یک نشست انجام می‌شوند.
    """

    async with AsyncSessionLocal() as session:
        existing_party = await session.scalar(
            select(Party)
            .join(
                PartyMember,
                PartyMember.party_id == Party.id,
            )
            .where(
                PartyMember.telegram_id == telegram_id,
                Party.status == "open",
            )
            .limit(1)
        )

        if existing_party is not None:
            return None, "قبلاً عضو یک پارتی هستی."

        party = Party(
            leader_telegram_id=telegram_id,
            name=name,
        )

        session.add(party)
        await session.flush()

        member = PartyMember(
            party_id=party.id,
            telegram_id=telegram_id,
        )

        session.add(member)
        await session.commit()
        await session.refresh(party)

        return party, "پارتی ساخته شد."


async def join_party(
    telegram_id: int,
    party_id: int,
) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        existing_party = await session.scalar(
            select(Party)
            .join(
                PartyMember,
                PartyMember.party_id == Party.id,
            )
            .where(
                PartyMember.telegram_id == telegram_id,
                Party.status == "open",
            )
            .limit(1)
        )

        if existing_party is not None:
            return False, "ابتدا از پارتی فعلی خارج شو."

        party = await session.scalar(
            select(Party).where(
                Party.id == party_id,
                Party.status == "open",
            )
        )

        if party is None:
            return False, "پارتی پیدا نشد."

        member_count = await session.scalar(
            select(func.count())
            .select_from(PartyMember)
            .where(PartyMember.party_id == party.id)
        )

        if member_count >= party.max_members:
            return False, "پارتی پر است."

        session.add(
            PartyMember(
                party_id=party.id,
                telegram_id=telegram_id,
            )
        )

        await session.commit()
        return True, "عضویت انجام شد."


async def leave_party(telegram_id: int) -> bool:
    """
    حذف عضویت بازیکن.

    اگر رهبر خارج شود، پارتی بسته خواهد شد.
    """

    async with AsyncSessionLocal() as session:
        member = await session.scalar(
            select(PartyMember).where(
                PartyMember.telegram_id == telegram_id
            )
        )

        if member is None:
            return False

        party = await session.scalar(
            select(Party).where(
                Party.id == member.party_id
            )
        )

        await session.delete(member)

        if party is not None and party.leader_telegram_id == telegram_id:
            party.status = "closed"

        await session.commit()
        return True


# ============================================================
# Guild
# ============================================================

async def create_guild(
    telegram_id: int,
    name: str,
    tag: str,
) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        existing_member = await session.scalar(
            select(GuildMember.id).where(
                GuildMember.telegram_id == telegram_id
            )
        )

        if existing_member:
            return False, "قبلاً عضو یک گیلد هستی."

        existing_guild = await session.scalar(
            select(Guild.id).where(
                (Guild.name == name) | (Guild.tag == tag)
            )
        )

        if existing_guild:
            return False, "نام یا تگ گیلد تکراری است."

        guild = Guild(
            name=name[:40],
            tag=tag[:8].upper(),
            owner_telegram_id=telegram_id,
        )

        session.add(guild)
        await session.flush()

        session.add(
            GuildMember(
                guild_id=guild.id,
                telegram_id=telegram_id,
                role="owner",
            )
        )

        await session.commit()
        return True, "گیلد ساخته شد."


async def guild_info(telegram_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Guild)
            .join(
                GuildMember,
                GuildMember.guild_id == Guild.id,
            )
            .where(
                GuildMember.telegram_id == telegram_id
            )
        )

        return result.scalar_one_or_none()


# ============================================================
# Dungeon
# ============================================================

async def start_dungeon(
    telegram_id: int,
    key: str = "eldoria_ruins",
) -> tuple[bool, str]:
    """
    ورود به دانجن فقط برای اعضای یک پارتی باز مجاز است.
    اجرای فعال به party_id متصل می‌شود تا همه اعضا یک اجرا داشته باشند.
    قفل ردیف پارتی از ساخت هم‌زمان چند اجرای فعال جلوگیری می‌کند.
    """
    async with AsyncSessionLocal() as session:
        party_id = await session.scalar(
            select(PartyMember.party_id)
            .join(Party, Party.id == PartyMember.party_id)
            .where(
                PartyMember.telegram_id == telegram_id,
                Party.status == "open",
            )
            .limit(1)
        )

        if party_id is None:
            return False, "برای ورود به دانجن باید عضو یک پارتی باز باشی."

        # قفل پارتی، ورود هم‌زمان چند عضو را سریالی می‌کند.
        party = await session.scalar(
            select(Party)
            .where(
                Party.id == party_id,
                Party.status == "open",
            )
            .with_for_update()
        )

        if party is None:
            return False, "پارتی فعالی پیدا نشد. دوباره تلاش کن."

        active = await session.scalar(
            select(DungeonRun)
            .where(
                DungeonRun.party_id == party.id,
                DungeonRun.status == "active",
            )
            .order_by(desc(DungeonRun.id))
            .limit(1)
            .with_for_update()
        )

        if active is not None:
            return (
                True,
                f"پارتی شما از قبل در دانجن فعال است. "
                f"دانجن: {active.dungeon_key}\n"
                f"طبقه فعلی: {active.floor}",
            )

        dungeon = DungeonRun(
            telegram_id=telegram_id,
            party_id=party.id,
            dungeon_key=key,
            floor=1,
            status="active",
        )
        session.add(dungeon)
        await session.commit()

        return (
            True,
            f"پارتی «{party.name}» وارد دانجن شد. "
            f"همه اعضای پارتی در همین اجرای مشترک هستند. "
            f"طبقه فعلی: 1",
        )


async def advance_dungeon(
    telegram_id: int,
) -> tuple[bool, str]:
    """پیشروی در اجرای مشترک دانجن، بر اساس پارتی بازیکن."""
    async with AsyncSessionLocal() as session:
        party_id = await session.scalar(
            select(PartyMember.party_id)
            .join(Party, Party.id == PartyMember.party_id)
            .where(
                PartyMember.telegram_id == telegram_id,
                Party.status == "open",
            )
            .limit(1)
        )

        if party_id is None:
            return False, "برای پیشروی در دانجن باید عضو یک پارتی باز باشی."

        dungeon = await session.scalar(
            select(DungeonRun)
            .where(
                DungeonRun.party_id == party_id,
                DungeonRun.status == "active",
            )
            .order_by(desc(DungeonRun.id))
            .limit(1)
            .with_for_update()
        )

        if dungeon is None:
            return False, "پارتی شما دانجن فعالی ندارد."

        dungeon.floor += 1
        dungeon.reward_gold = dungeon.floor * 100

        if dungeon.floor >= 5:
            dungeon.status = "completed"

        floor = dungeon.floor
        reward = dungeon.reward_gold
        completed = dungeon.status == "completed"
        await session.commit()

        if completed:
            return (
                True,
                f"پارتی شما دانجن را کامل کرد! "
                f"طبقه نهایی: {floor}. پاداش ثبت‌شده: {reward:,} Gold",
            )

        return (
            True,
            f"طبقه {floor} برای تمام اعضای پارتی پاکسازی شد. "
            f"پاداش ثبت‌شده: {reward:,} Gold",
        )


# سازگاری با نام استفاده‌شده در handler
async def enter_dungeon(telegram_id: int):
    return await start_dungeon(telegram_id)


# ============================================================
# PvP
# ============================================================

async def create_pvp_challenge(
    telegram_id: int,
    opponent_telegram_id: int,
) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        if telegram_id == opponent_telegram_id:
            return False, "نمی‌توانی خودت را به مبارزه دعوت کنی."

        player = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        opponent = await session.scalar(
            select(Character).where(
                Character.telegram_id == opponent_telegram_id
            )
        )

        if player is None or opponent is None:
            return False, "هر دو بازیکن باید شخصیت داشته باشند."

        challenge = PvpChallenge(
            challenger_telegram_id=telegram_id,
            opponent_telegram_id=opponent_telegram_id,
        )

        session.add(challenge)
        await session.commit()

        return True, "درخواست PvP ارسال شد."


# ============================================================
# Ranking
# ============================================================

async def ranking(limit: int = 10):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Character)
            .order_by(
                desc(Character.level),
                desc(Character.xp),
                desc(Character.gold),
            )
            .limit(limit)
        )

        return list(result.scalars().all())


# سازگاری با نام استفاده‌شده در handler
async def get_ranking(limit: int = 10):
    return await ranking(limit)


# ============================================================
# Crafting
# ============================================================

async def recipes():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CraftRecipe)
            .where(CraftRecipe.is_active.is_(True))
            .order_by(CraftRecipe.id)
        )

        return list(result.scalars().all())


async def craft(
    telegram_id: int,
    recipe_id: int,
    quantity: int = 1,
) -> tuple[bool, str]:
    """ساخت اتمیک آیتم‌ها؛ همهٔ مواد و Gold پیش از کسر بررسی می‌شوند."""
    from models.inventory import Inventory
    from models.item import Item
    from models.equipment import Equipment, CharacterEquipment

    if quantity not in {1, 5, 10, 20, 50}:
        return False, "تعداد ساخت انتخاب‌شده معتبر نیست."

    async with AsyncSessionLocal() as session:
        async with session.begin():
            player = await session.scalar(
                select(Character).where(
                    Character.telegram_id == telegram_id
                ).with_for_update()
            )
            recipe = await session.scalar(
                select(CraftRecipe).where(
                    CraftRecipe.id == recipe_id,
                    CraftRecipe.is_active.is_(True),
                )
            )

            if player is None or recipe is None:
                return False, "قهرمان یا دستور ساخت پیدا نشد."
            if player.level < recipe.required_level:
                return False, f"برای این دستور حداقل سطح {recipe.required_level} لازم است."

            total_gold = int(recipe.gold_cost or 0) * quantity
            if player.gold < total_gold:
                return False, f"Gold کافی نیست؛ هزینهٔ این ساخت {total_gold:,} Gold است."

            try:
                materials = json.loads(recipe.materials_json or "{}")
            except (TypeError, ValueError):
                return False, "اطلاعات مواد اولیهٔ این دستور معتبر نیست."

            needed: dict[int, int] = {}
            for raw_id, raw_amount in materials.items():
                item_id, amount = int(raw_id), int(raw_amount) * quantity
                if item_id <= 0 or amount <= 0:
                    return False, "اطلاعات مواد اولیهٔ این دستور معتبر نیست."
                needed[item_id] = amount

            inventory_items = {}
            for item_id, amount in needed.items():
                inv = await session.scalar(
                    select(Inventory).where(
                        Inventory.character_id == player.id,
                        Inventory.item_id == item_id,
                    ).with_for_update()
                )
                if inv is None or inv.quantity < amount:
                    item = await session.get(Item, item_id)
                    item_name = item.name if item else f"مادهٔ #{item_id}"
                    have = inv.quantity if inv else 0
                    return False, f"مواد کافی نیست: {item_name} ({have}/{amount})."
                inventory_items[item_id] = (inv, amount)

            # Recipe output is validated before any resource is consumed.
            output_item = None
            output_equipment = None
            if recipe.result_item_id is not None:
                output_item = await session.get(Item, recipe.result_item_id)
                if output_item is None:
                    return False, "آیتم خروجی دستور ساخت در دیتابیس وجود ندارد."
            elif recipe.result_equipment_id is not None:
                output_equipment = await session.get(Equipment, recipe.result_equipment_id)
                if output_equipment is None or not output_equipment.is_active:
                    return False, "تجهیز خروجی دستور ساخت در دیتابیس وجود ندارد یا غیرفعال است."
                if player.level < int(output_equipment.required_level or 1):
                    return False, f"برای ساخت این تجهیز باید حداقل سطح {output_equipment.required_level} را داشته باشی."
            else:
                return False, "این دستور خروجی معتبری ندارد؛ با مدیر بازی تماس بگیر."

            for inv, amount in inventory_items.values():
                inv.quantity -= amount
                if inv.quantity <= 0:
                    await session.delete(inv)

            player.gold -= total_gold
            if output_item is not None:
                output_inv = await session.scalar(
                    select(Inventory).where(
                        Inventory.character_id == player.id,
                        Inventory.item_id == recipe.result_item_id,
                    ).with_for_update()
                )
                if output_inv is None:
                    session.add(Inventory(
                        character_id=player.id,
                        item_id=recipe.result_item_id,
                        quantity=quantity,
                    ))
                else:
                    output_inv.quantity += quantity
            else:
                output_equipment_inventory = await session.scalar(
                    select(CharacterEquipment).where(
                        CharacterEquipment.character_id == player.id,
                        CharacterEquipment.equipment_id == recipe.result_equipment_id,
                    ).with_for_update()
                )
                if output_equipment_inventory is None:
                    session.add(CharacterEquipment(
                        character_id=player.id,
                        equipment_id=recipe.result_equipment_id,
                        quantity=quantity,
                        equipped=False,
                    ))
                else:
                    output_equipment_inventory.quantity += quantity

            # XP کرفتینگ در همان تراکنش ذخیره می‌شود.
            player.crafting_xp = int(player.crafting_xp or 0) + (5 * quantity)
            output_name = output_item.name if output_item is not None else output_equipment.name

        return True, (
            f"ساخت موفق بود: {quantity}× {output_name}\n"
            f"هزینه: {total_gold:,} Gold\n"
            f"XP کرفتینگ: +{5 * quantity}"
        )


# ============================================================
# Pets
# ============================================================

async def active_pets(telegram_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Pet, CharacterPet)
            .join(
                CharacterPet,
                CharacterPet.pet_id == Pet.id,
            )
            .join(
                Character,
                Character.id == CharacterPet.character_id,
            )
            .where(
                Character.telegram_id == telegram_id
            )
        )

        return list(result.all())


async def activate_pet(
    telegram_id: int,
    pet_id: int,
) -> tuple[bool, str]:
    async with AsyncSessionLocal() as session:
        player = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if player is None:
            return False, "قهرمان پیدا نشد."

        character_pet = await session.scalar(
            select(CharacterPet).where(
                CharacterPet.character_id == player.id,
                CharacterPet.pet_id == pet_id,
            )
        )

        if character_pet is None:
            return False, "این پت را نداری."

        await session.execute(
            update(CharacterPet)
            .where(
                CharacterPet.character_id == player.id
            )
            .values(active=False)
        )

        character_pet.active = True

        await session.commit()
        return True, "پت فعال شد."


# ============================================================
# Events
# ============================================================

async def events():
    now = datetime.utcnow()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GameEvent)
            .where(
                GameEvent.is_active.is_(True),
                GameEvent.starts_at <= now,
                GameEvent.ends_at >= now,
            )
            .order_by(GameEvent.ends_at)
        )

        return list(result.scalars().all())