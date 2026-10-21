from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.inventory import Inventory
from models.item import Item
from models.social_systems import DungeonLoot, GroupDungeonEvent, Party, PartyMember
from models.world_systems import GroupBoss
from services.xp_service import add_character_xp
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

DUNGEON_POOL = [
    {"key": "zareth_catacombs", "name": "⚰️ دخمه‌های مُهرشدهٔ زارِث", "difficulty": "I · فراموش‌شده", "level": 1, "duration": 30, "loot": (1, 3), "xp": (80, 180), "skill_xp": (25, 60), "gold": (80, 180)},
    {"key": "nihar_mirror_halls", "name": "🪞 تالارهای آینهٔ نیهار", "difficulty": "II · نفرین‌شده", "level": 15, "duration": 45, "loot": (2, 4), "xp": (180, 380), "skill_xp": (60, 130), "gold": (180, 420)},
    {"key": "vergall_sunken_keep", "name": "🏰 دژِ فرورفتهٔ وِرگال", "difficulty": "III · باستانی", "level": 35, "duration": 60, "loot": (3, 5), "xp": (350, 700), "skill_xp": (120, 260), "gold": (350, 800)},
    {"key": "ormaween_night_rift", "name": "🌘 شکاف شبِ اُرماوِن", "difficulty": "IV · تاریک", "level": 60, "duration": 90, "loot": (4, 7), "xp": (700, 1300), "skill_xp": (250, 500), "gold": (700, 1600)},
    {"key": "last_star_abyss", "name": "🌌 مغاکِ ستارهٔ واپسین", "difficulty": "V · اسطوره‌ای", "level": 85, "duration": 120, "loot": (6, 9), "xp": (1300, 2400), "skill_xp": (450, 900), "gold": (1500, 3500)},
]
LOOT_POOL = [
    ("zareth_sealshard", "پاره‌مُهرِ زارِث", 7),
    ("nihar_violet_tear", "اشکِ بنفشِ نیهار", 14),
    ("vergall_silent_crown", "تاجِ خاموشانِ وِرگال", 32),
    ("ormaween_cursed_crescent", "هلالِ نفرین‌شدهٔ اُرماوِن", 26),
    ("last_star_dust", "غبارِ ستارهٔ واپسین", 19),
    ("ashblood_dragon_scale", "فلسِ اژدهای گورستانِ آذرخون", 55),
    ("moonless_orb", "گویِ بی‌ماه سِرادین", 82),
    ("eclipsed_signet", "نگینِ کسوفِ وارثان", 120),
    ("thousand_whispers_relic", "یادگارِ هزار نجوا", 175),
    ("voidheart_fragment", "خرده‌قلبِ خلأ", 260),
]

def _load_ids(raw: str | None) -> list[int]:
    try:
        return [int(x) for x in json.loads(raw or "[]")]
    except (ValueError, TypeError):
        return []

async def spawn_group_dungeon(chat_id: int, chat_title: str | None = None, *, force: bool = False):
    now = datetime.utcnow()
    cfg = random.choice(DUNGEON_POOL)
    async with AsyncSessionLocal() as session:
        event = await session.scalar(select(GroupDungeonEvent).where(GroupDungeonEvent.chat_id == chat_id).with_for_update())
        if event and event.status in {"forming", "running"}:
            return False, "در این گپ یک دانجن در حال آماده‌سازی یا اجراست."
        if event and event.status == "waiting" and event.spawned_at and now < event.spawned_at + timedelta(minutes=30):
            return False, "در این گپ هنوز یک دانجن برای ورود باز است؛ برای جلوگیری از تداخل، ابتدا مهلت آن باید تمام شود."
        if event is None:
            event = GroupDungeonEvent(chat_id=chat_id, chat_title=(chat_title or "گروه اِلدوریا")[:255], next_spawn_at=now)
            session.add(event)
        event.chat_title = (chat_title or event.chat_title or "گروه اِلدوریا")[:255]
        event.dungeon_key = cfg["key"]
        event.dungeon_name = cfg["name"]
        event.difficulty = cfg["difficulty"]
        event.recommended_level = cfg["level"]
        event.duration_minutes = cfg["duration"]
        event.status = "waiting"
        event.spawned_at = now
        event.next_spawn_at = now + timedelta(hours=1)
        event.party_id = None
        event.leader_telegram_id = None
        event.members_json = "[]"
        event.ready_json = "[]"
        event.ready_deadline = None
        event.run_started_at = None
        event.finishes_at = None
        event.message_id = None
        await session.commit()
        await session.refresh(event)
        return True, {"id": event.id, "chat_id": chat_id, "chat_title": event.chat_title, **cfg, "spawned_at": now}

async def get_group_event(chat_id: int):
    async with AsyncSessionLocal() as session:
        return await session.scalar(select(GroupDungeonEvent).where(GroupDungeonEvent.chat_id == chat_id))

async def set_event_message(chat_id: int, message_id: int):
    async with AsyncSessionLocal() as session:
        event = await session.scalar(select(GroupDungeonEvent).where(GroupDungeonEvent.chat_id == chat_id))
        if event:
            event.message_id = message_id
            await session.commit()

async def join_dungeon(chat_id: int, telegram_id: int):
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        event = await session.scalar(select(GroupDungeonEvent).where(GroupDungeonEvent.chat_id == chat_id).with_for_update())
        if event is None or event.status != "waiting" or not event.spawned_at or now >= event.spawned_at + timedelta(minutes=30):
            return False, "این دروازه بسته شده؛ منتظر ظهور دانجن بعدی بمان.", None
        party_id = await session.scalar(select(PartyMember.party_id).join(Party, Party.id == PartyMember.party_id).where(PartyMember.telegram_id == telegram_id, Party.status == "open").limit(1))
        if party_id is None:
            return False, "برای ورود باید عضو یک پارتی فعال باشی.", None
        party = await session.scalar(select(Party).where(Party.id == party_id).with_for_update())
        members = list((await session.scalars(select(PartyMember.telegram_id).where(PartyMember.party_id == party_id).order_by(PartyMember.joined_at, PartyMember.id))).all())
        if not members:
            return False, "اعضای پارتی پیدا نشدند.", None
        # Only one party can reserve this group's current dungeon.
        if event.party_id is not None and event.party_id != party_id:
            return False, "این دانجن را پارتی دیگری رزرو کرده است.", None
        if event.party_id == party_id and event.status == "forming":
            ready = _load_ids(event.ready_json)
            reserved_members = _load_ids(event.members_json)
            if telegram_id not in reserved_members or telegram_id not in members:
                return False, "فقط اعضای پارتی هنگام رزرو دروازه می‌توانند آماده شوند.", None
            if telegram_id not in ready:
                ready.append(telegram_id)
                event.ready_json = json.dumps(ready)
                await session.commit()
            return True, "آمادگی‌ات ثبت شد.", {"event": event, "members": reserved_members, "ready": ready}
        # Validate all party members have a character; only players who press Ready join.
        existing = set((await session.scalars(select(Character.telegram_id).where(Character.telegram_id.in_(members)))).all())
        members = [int(x) for x in members if int(x) in existing]
        if telegram_id not in members:
            return False, "شخصیتت در این پارتی پیدا نشد.", None
        event.party_id = party_id
        event.leader_telegram_id = telegram_id
        event.members_json = json.dumps(members)
        event.ready_json = json.dumps([telegram_id])
        event.status = "forming"
        event.ready_deadline = now + timedelta(minutes=1)
        await session.commit()
        return True, f"پارتی «{party.name}» دروازه را رزرو کرد؛ اعضا تا یک دقیقه برای اعلام آمادگی فرصت دارند.", {"event": event, "members": members, "ready": [telegram_id]}

async def get_dungeon_loot(telegram_id: int):
    async with AsyncSessionLocal() as session:
        return list((await session.scalars(select(DungeonLoot).where(DungeonLoot.telegram_id == telegram_id, DungeonLoot.quantity > 0).order_by(DungeonLoot.item_name))).all())

async def sell_all_dungeon_loot(telegram_id: int):
    async with AsyncSessionLocal() as session:
        rows = list((await session.scalars(select(DungeonLoot).where(DungeonLoot.telegram_id == telegram_id, DungeonLoot.quantity > 0).with_for_update())).all())
        if not rows:
            return False, "صندوق غنیمت دانجنت خالی است.", 0, []
        character = await session.scalar(select(Character).where(Character.telegram_id == telegram_id).with_for_update())
        if character is None:
            return False, "شخصیتت پیدا نشد.", 0, []
        total = sum(int(row.quantity) * int(row.unit_gold) for row in rows)
        character.gold = min(2_147_483_647, int(character.gold or 0) + total)
        sold = [(row.item_name, int(row.quantity), int(row.unit_gold)) for row in rows]
        for row in rows:
            row.quantity = 0
        await session.commit()
        return True, "غنیمت‌ها با موفقیت فروخته شدند.", total, sold

async def _grant_loot(session, telegram_id: int, cfg: dict):
    character = await session.scalar(select(Character).where(Character.telegram_id == telegram_id).with_for_update())
    if character is None:
        return None
    xp = random.randint(*cfg["xp"])
    skill_xp = random.randint(*cfg["skill_xp"])
    gold = random.randint(*cfg["gold"])
    character.skill_xp = int(character.skill_xp or 0) + skill_xp
    character.gold = min(2_147_483_647, int(character.gold or 0) + gold)
    # Potions are ordinary consumables; dungeon collectibles remain in their own table.
    potion_names = ["🧪 معجون سلامتی", "🧪 معجون سلامتی بزرگ", "🔷 معجون مانا", "🧪 معجون مانای بزرگ"]
    potion_rewards = []
    potion_count = 1 if cfg["level"] < 35 else random.randint(1, 2)
    for _ in range(potion_count):
        item_name = random.choice(potion_names[:2] if random.random() < 0.5 else potion_names[2:])
        item = await session.scalar(select(Item).where(Item.name == item_name, Item.item_type == "potion"))
        if item:
            inv = await session.scalar(select(Inventory).where(Inventory.character_id == character.id, Inventory.item_id == item.id).with_for_update())
            if inv:
                inv.quantity += 1
            else:
                session.add(Inventory(character_id=character.id, item_id=item.id, quantity=1))
            potion_rewards.append(item_name)
    n = random.randint(*cfg["loot"])
    drops = []
    pool = LOOT_POOL[:4] if cfg["level"] < 15 else LOOT_POOL[:6] if cfg["level"] < 35 else LOOT_POOL[:8] if cfg["level"] < 60 else LOOT_POOL
    for _ in range(n):
        key, name, value = random.choice(pool)
        value = max(1, int(value * random.uniform(0.8, 1.25) * (1 if cfg["level"] < 35 else cfg["level"] / 30)))
        loot = await session.scalar(select(DungeonLoot).where(DungeonLoot.telegram_id == telegram_id, DungeonLoot.item_key == key).with_for_update())
        if loot:
            loot.quantity += 1
            loot.unit_gold = max(loot.unit_gold, value)
        else:
            session.add(DungeonLoot(telegram_id=telegram_id, item_key=key, item_name=name, quantity=1, unit_gold=value))
        drops.append((name, value))
    return {"name": character.name, "xp": xp, "skill_xp": skill_xp, "gold": gold, "potions": potion_rewards, "drops": drops}

async def finish_due_dungeons(bot):
    now = datetime.utcnow()
    # Read IDs first; each event is locked independently for idempotent state transitions.
    async with AsyncSessionLocal() as session:
        ids = list((await session.scalars(select(GroupDungeonEvent.id).where(GroupDungeonEvent.status.in_(["waiting", "forming", "running"])))).all())
    for event_id in ids:
        rewards = []
        notification = None
        async with AsyncSessionLocal() as session:
            event = await session.scalar(select(GroupDungeonEvent).where(GroupDungeonEvent.id == event_id).with_for_update())
            if not event:
                continue
            if event.status == "waiting" and event.spawned_at and now >= event.spawned_at + timedelta(minutes=30):
                event.status = "expired"
                event.next_spawn_at = event.spawned_at + timedelta(hours=1)
                notification = (event.chat_id, event.message_id, "⌛ <b>دروازهٔ دانجن بسته شد.</b>\nهیچ پارتی در مهلت مقرر وارد نشد؛ تا ظهور بعدی صبر کنید.")
            elif event.status == "forming" and event.ready_deadline and now >= event.ready_deadline:
                ready = _load_ids(event.ready_json)
                if not ready:
                    event.status = "expired"
                    event.next_spawn_at = (event.spawned_at or now) + timedelta(hours=1)
                    notification = (event.chat_id, event.message_id, "🌫️ هیچ قهرمانی اعلام آمادگی نکرد؛ دروازه فروبست.")
                else:
                    cfg = next((d for d in DUNGEON_POOL if d["key"] == event.dungeon_key), DUNGEON_POOL[0])
                    # Persist only those who pressed Ready; reward once when status flips to running.
                    event.members_json = json.dumps(ready)
                    event.status = "running"
                    event.run_started_at = now
                    event.finishes_at = now + timedelta(minutes=event.duration_minutes)
                    notification = (event.chat_id, event.message_id, f"🌀 <b>گروه وارد {event.dungeon_name} شد!</b>\n⏳ زمان اکتشاف: <b>{event.duration_minutes} دقیقه</b>\nپاداش‌ها پس از پایان مسیر به پیام خصوصی ارسال می‌شوند.")
            elif event.status == "running" and event.finishes_at and now >= event.finishes_at:
                cfg = next((d for d in DUNGEON_POOL if d["key"] == event.dungeon_key), DUNGEON_POOL[0])
                for uid in _load_ids(event.members_json):
                    reward = await _grant_loot(session, uid, cfg)
                    if reward:
                        rewards.append((uid, reward))
                event.status = "completed"
                event.next_spawn_at = (event.spawned_at or now) + timedelta(hours=1)
                notification = (event.chat_id, event.message_id, f"🏆 <b>اکتشاف {event.dungeon_name} به پایان رسید!</b>\nاعضای شرکت‌کننده پاداش‌های خود را در پیام خصوصی دریافت می‌کنند.")
            await session.commit()
        if notification:
            chat_id, message_id, text = notification
            try:
                if message_id:
                    await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=None, parse_mode="HTML")
                else:
                    await bot.send_message(chat_id, text, parse_mode="HTML")
            except Exception:
                try: await bot.send_message(chat_id, text, parse_mode="HTML")
                except Exception: pass
        for uid, reward in rewards:
            # Use the central XP service so rewards trigger normal level-ups and stat growth.
            try:
                await add_character_xp(uid, int(reward["xp"]))
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Could not apply dungeon XP for player %s", uid)
            lines = [f"🏆 <b>گزارش اکتشاف: {reward['name']}</b>", "", f"✨ تجربه: <b>+{reward['xp']:,} XP</b>", f"🔮 تجربهٔ مهارت: <b>+{reward['skill_xp']:,}</b>", f"💰 گلد مستقیم: <b>+{reward['gold']:,}</b>", "", "<b>🧪 معجون‌ها</b>"]
            lines.extend([f"• {name}" for name in reward["potions"]] or ["• این بار معجونی پیدا نشد"])
            lines.extend(["", "<b>🗝 غنیمت‌های اختصاصی دانجن</b>"])
            lines.extend([f"• {name} · ارزش فروش: 💰 {value:,}" for name, value in reward["drops"]])
            lines.extend(["", "برای دیدن موجودی غنیمت‌ها و فروش همه، دستور <b>غنیمت دانجن</b> را در خصوصی ربات یا گروه بفرست."])
            try:
                await bot.send_message(uid, "\n".join(lines), parse_mode="HTML")
            except Exception:
                # Rewards are persisted before notification, so a blocked DM does not lose them.
                pass

async def dungeon_scheduler(bot):
    while True:
        try:
            await finish_due_dungeons(bot)
            now = datetime.utcnow()
            async with AsyncSessionLocal() as session:
                groups = list((await session.scalars(select(GroupBoss).order_by(GroupBoss.chat_id))).all())
                for group in groups:
                    event = await session.scalar(select(GroupDungeonEvent).where(GroupDungeonEvent.chat_id == group.chat_id))
                    should_spawn = event is None or (event.status in {"expired", "completed"} and event.next_spawn_at <= now) or (event.status == "waiting" and event.spawned_at and now >= event.spawned_at + timedelta(hours=1))
                    if not should_spawn:
                        continue
                    # Avoid holding an old session across Telegram network calls.
                    chat_id, title = int(group.chat_id), group.chat_title
                    ok, result = await spawn_group_dungeon(chat_id, title)
                    if not ok:
                        continue
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚪 ورود به دانجن", callback_data="dungeon:enter")], [InlineKeyboardButton(text="📜 قوانین اکتشاف", callback_data="dungeon:rules")]])
                    caption = render_spawn_text(result)
                    try:
                        sent = await bot.send_message(chat_id, caption, reply_markup=keyboard, parse_mode="HTML")
                        await set_event_message(chat_id, sent.message_id)
                    except Exception:
                        # Keep next spawn bounded; if bot cannot post, retry in five minutes.
                        async with AsyncSessionLocal() as retry_session:
                            row = await retry_session.scalar(select(GroupDungeonEvent).where(GroupDungeonEvent.chat_id == chat_id))
                            if row:
                                row.next_spawn_at = datetime.utcnow() + timedelta(minutes=5)
                                row.status = "expired"
                                await retry_session.commit()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Dungeon scheduler iteration failed")
        import asyncio
        await asyncio.sleep(20)

def render_spawn_text(data: dict) -> str:
    return (f"🌌 <b>شکاف میان‌جهان گشوده شد!</b>\n\n<b>{data['name']}</b>\n" 
            f"🧭 درجه: <b>{data['difficulty']}</b>\n🎚 سطح پیشنهادی: <b>{data['level']}+</b>\n"
            f"⏳ زمان اکتشاف: <b>{data['duration']} دقیقه</b>\n\n"
            "👥 فقط یک پارتی می‌تواند این دروازه را رزرو کند. نخستین عضو پارتی که وارد شود، یک دقیقه برای اعلام آمادگی اعضا فرصت ایجاد می‌کند.\n"
            "⌛ اگر طی ۳۰ دقیقه هیچ پارتی وارد نشود، دروازه ناپدید می‌شود.")
