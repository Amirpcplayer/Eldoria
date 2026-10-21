from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.character_skill import CharacterSkill
from models.inventory import Inventory
from models.item import Item
from models.skill import Skill
from models.social_systems import DungeonRun, GroupDungeonState, Party, PartyMember
from services.equipment_service import get_final_character_stats
from services.skill_service import get_skill_mana_cost, get_skill_power
from services.xp_service import add_character_xp

DUNGEONS = {
    "eldoria_ruins": {"name": "ویرانه‌های اِلدوریا", "floors": 5, "boss": "نگهبان ویرانه‌ها", "base_hp": 180},
    "forgotten_crypt": {"name": "سرداب فراموش‌شده", "floors": 7, "boss": "پادشاه مردگان", "base_hp": 240},
    "eternal_flame_fortress": {"name": "دژ شعلهٔ ابدی", "floors": 8, "boss": "سالار آتش", "base_hp": 300},
    "frozen_temple": {"name": "معبد یخ‌زده", "floors": 6, "boss": "اژدهای یخی", "base_hp": 220},
    "shadow_abyss": {"name": "ژرفای سایه", "floors": 9, "boss": "فرمانروای سایه", "base_hp": 360},
    "ancient_dragon_realm": {"name": "قلمرو اژدهای باستانی", "floors": 10, "boss": "اژدهای باستانی", "base_hp": 450},
}
TURN_SECONDS = 60
POTION_HEAL = {"🧪 معجون سلامتی": 5_000, "🧪 معجون سلامتی بزرگ": 25_000}


def _enemy(dungeon_key: str, floor: int, party_size: int) -> tuple[str, int]:
    cfg = DUNGEONS[dungeon_key]
    if floor == cfg["floors"]:
        return cfg["boss"], cfg["base_hp"] * max(1, party_size)
    names = ["نگهبان سنگی", "شکارچی تاریکی", "غول باستانی", "جادوگر تباه‌شده"]
    return names[(floor - 1) % len(names)], (70 + floor * 35) * max(1, party_size)


async def _party_and_members(session, telegram_id: int):
    party_id = await session.scalar(
        select(PartyMember.party_id).join(Party, Party.id == PartyMember.party_id)
        .where(PartyMember.telegram_id == telegram_id, Party.status == "open").limit(1)
    )
    if party_id is None:
        return None, []
    party = await session.scalar(select(Party).where(Party.id == party_id).with_for_update())
    members = (await session.execute(
        select(PartyMember.telegram_id).where(PartyMember.party_id == party_id)
        .order_by(PartyMember.joined_at, PartyMember.id)
    )).scalars().all()
    return party, [int(x) for x in members]


def _state_dict(state, members=None):
    try:
        members = members if members is not None else json.loads(state.members_json or "[]")
    except (ValueError, TypeError):
        members = []
    try:
        actions = json.loads(state.actions_json or "{}")
    except (ValueError, TypeError):
        actions = {}
    return {
        "id": state.id, "party_id": state.party_id, "dungeon_key": state.dungeon_key,
        "floor": state.floor, "floor_count": state.floor_count, "enemy_name": state.enemy_name,
        "enemy_hp": state.enemy_hp, "enemy_max_hp": state.enemy_max_hp, "members": members,
        "actions": actions, "turn_index": state.turn_index, "turn_started_at": state.turn_started_at,
        "status": state.status,
    }


async def get_group_dungeon_profiles(member_ids: list[int]) -> list[dict]:
    """Return live character resources and equipment-derived combat stats for the shared panel."""
    if not member_ids:
        return []
    async with AsyncSessionLocal() as session:
        chars = (await session.execute(select(Character).where(Character.telegram_id.in_(member_ids)))).scalars().all()
        by_id = {int(c.telegram_id): c for c in chars}
        profiles = []
        for member_id in member_ids:
            char = by_id.get(int(member_id))
            if char is None:
                continue
            stats = await get_final_character_stats(int(member_id))
            max_hp = max(1, int(stats.get("hp", char.max_hp or 100)))
            max_mana = max(1, int(stats.get("mana", char.max_mana or 100)))
            profiles.append({
                "telegram_id": int(member_id), "name": str(char.name), "level": int(char.level or 1),
                "hp": min(max_hp, max(0, int(char.hp or 0))), "max_hp": max_hp,
                "mana": min(max_mana, max(0, int(char.mana or 0))), "max_mana": max_mana,
                "attack": max(1, int(stats.get("attack", char.attack or 1))),
                "magic_power": max(0, int(stats.get("magic_power", char.magic_power or 0))),
                "defense": max(0, int(stats.get("defense", char.defense or 0))),
                "magic_defense": max(0, int(stats.get("magic_defense", char.magic_defense or 0))),
                "speed": max(0, int(stats.get("speed", char.speed or 0))),
                "accuracy": max(0, int(stats.get("accuracy", char.accuracy or 0))),
                "critical": max(0, int(stats.get("critical", char.critical or 0))),
            })
        return profiles


async def get_group_dungeon_skills(telegram_id: int) -> list[dict]:
    async with AsyncSessionLocal() as session:
        char = await session.scalar(select(Character).where(Character.telegram_id == telegram_id))
        if char is None:
            return []
        rows = (await session.execute(
            select(Skill, CharacterSkill).join(CharacterSkill, CharacterSkill.skill_id == Skill.id)
            .where(CharacterSkill.character_id == char.id, CharacterSkill.unlocked.is_(True), Skill.is_active.is_(True))
            .order_by(CharacterSkill.slot, Skill.id)
        )).all()
        result = []
        for skill, learned in rows:
            cost = get_skill_mana_cost(skill, int(learned.level or 1))
            result.append({"id": int(skill.id), "name": str(skill.name), "element": str(skill.element),
                           "level": int(learned.level or 1), "mana_cost": int(cost),
                           "power": int(get_skill_power(skill, int(learned.level or 1))),
                           "skill_type": str(skill.skill_type), "target_type": str(skill.target_type)})
        return result


async def get_group_dungeon_potions(telegram_id: int) -> list[dict]:
    async with AsyncSessionLocal() as session:
        char = await session.scalar(select(Character).where(Character.telegram_id == telegram_id))
        if char is None:
            return []
        rows = (await session.execute(
            select(Inventory, Item).join(Item, Item.id == Inventory.item_id)
            .where(Inventory.character_id == char.id, Inventory.quantity > 0, Item.item_type == "potion")
            .order_by(Item.id)
        )).all()
        return [{"id": int(item.id), "name": str(item.name), "quantity": int(inv.quantity),
                 "heal": int(POTION_HEAL.get(str(item.name), 0))}
                for inv, item in rows if POTION_HEAL.get(str(item.name), 0) > 0]


async def start_group_dungeon(telegram_id: int, dungeon_key: str = "eldoria_ruins"):
    if dungeon_key not in DUNGEONS:
        return False, "این دانجن معتبر نیست.", None
    async with AsyncSessionLocal() as session:
        party, members = await _party_and_members(session, telegram_id)
        if party is None:
            return False, "برای ورود به دانجن باید عضو یک پارتی باز باشی.", None
        if int(party.leader_telegram_id) != telegram_id:
            return False, "فقط رهبر پارتی می‌تواند دانجن را آغاز کند.", None
        state = await session.scalar(select(GroupDungeonState).where(GroupDungeonState.party_id == party.id).with_for_update())
        if state is not None and state.status == "active":
            return True, "دانجن پارتی از قبل فعال است.", _state_dict(state, members)
        existing = (await session.execute(select(Character.telegram_id).where(Character.telegram_id.in_(members)))).scalars().all() if members else []
        members = [int(x) for x in existing]
        if not members:
            return False, "اعضای پارتی باید ابتدا شخصیت بسازند.", None
        name, hp = _enemy(dungeon_key, 1, len(members))
        values = dict(dungeon_key=dungeon_key, floor=1, floor_count=DUNGEONS[dungeon_key]["floors"], enemy_name=name,
                      enemy_hp=hp, enemy_max_hp=hp, members_json=json.dumps(members), actions_json="{}",
                      turn_index=0, turn_started_at=datetime.utcnow(), status="active")
        if state is None:
            state = GroupDungeonState(party_id=party.id, **values)
            session.add(state)
        else:
            for key, value in values.items():
                setattr(state, key, value)
        for member_id in members:
            run = await session.scalar(select(DungeonRun).where(DungeonRun.telegram_id == member_id, DungeonRun.status == "active").limit(1))
            if run is None:
                session.add(DungeonRun(telegram_id=member_id, party_id=party.id, dungeon_key=dungeon_key, floor=1, status="active", reward_gold=0))
        await session.commit()
        await session.refresh(state)
        return True, f"پارتی «{party.name}» وارد «{DUNGEONS[dungeon_key]['name']}» شد.", _state_dict(state, members)


async def get_group_dungeon(telegram_id: int):
    async with AsyncSessionLocal() as session:
        party, members = await _party_and_members(session, telegram_id)
        if party is None:
            return False, "برای مشاهدهٔ دانجن باید عضو پارتی باشی.", None
        state = await session.scalar(select(GroupDungeonState).where(GroupDungeonState.party_id == party.id))
        if state is None:
            return False, "پارتی هنوز دانجنی را آغاز نکرده است.", None
        # Keep order aligned with the current party membership; removed members cannot act.
        try:
            saved = [int(x) for x in json.loads(state.members_json or "[]")]
        except (ValueError, TypeError):
            saved = members
        order = [mid for mid in saved if mid in members]
        # The shared panel must show the real current turn even if nobody clicked an action.
        now = datetime.utcnow()
        if state.status == "active" and order:
            state.turn_index %= len(order)
            while now - state.turn_started_at >= timedelta(seconds=TURN_SECONDS):
                state.turn_index = (state.turn_index + 1) % len(order)
                state.turn_started_at += timedelta(seconds=TURN_SECONDS)
            await session.commit()
        return True, "وضعیت دانجن", _state_dict(state, order)


async def group_dungeon_action(telegram_id: int, action: str, *, skill_id: int | None = None, item_id: int | None = None):
    if action not in {"attack", "skill", "potion"}:
        return False, "اقدام نامعتبر است.", None
    now = datetime.utcnow()
    eligible_rewards: list[int] = []
    async with AsyncSessionLocal() as session:
        party, current_members = await _party_and_members(session, telegram_id)
        if party is None:
            return False, "دانجن گروهی فقط در پارتی قابل اجراست.", None
        state = await session.scalar(select(GroupDungeonState).where(GroupDungeonState.party_id == party.id).with_for_update())
        if state is None or state.status != "active":
            return False, "دانجن فعالی وجود ندارد.", None
        try:
            order = [int(x) for x in json.loads(state.members_json or "[]") if int(x) in current_members]
        except (ValueError, TypeError):
            order = current_members
        if not order:
            return False, "هیچ عضو فعالی برای مبارزه وجود ندارد.", _state_dict(state, [])
        while now - state.turn_started_at >= timedelta(seconds=TURN_SECONDS):
            state.turn_index = (state.turn_index + 1) % len(order)
            state.turn_started_at += timedelta(seconds=TURN_SECONDS)
        state.turn_index %= len(order)
        if order[state.turn_index] != telegram_id:
            left = max(1, TURN_SECONDS - int((now - state.turn_started_at).total_seconds()))
            await session.commit()
            return False, f"نوبت بازیکن دیگری است؛ {left} ثانیه تا پایان نوبت او باقی مانده.", _state_dict(state, order)

        char = await session.scalar(select(Character).where(Character.telegram_id == telegram_id).with_for_update())
        if char is None:
            return False, "شخصیت پیدا نشد.", None
        stats = await get_final_character_stats(telegram_id)
        max_hp = max(1, int(stats.get("hp", char.max_hp or 100)))
        max_mana = max(1, int(stats.get("mana", char.max_mana or 100)))
        char.max_hp, char.max_mana = max_hp, max_mana
        char.hp = min(max_hp, max(0, int(char.hp or 0)))
        char.mana = min(max_mana, max(0, int(char.mana or 0)))
        if char.hp <= 0:
            return False, "❤️ HP شخصیتت صفر است؛ بعد از شکست باید برای شروع مجدد وضعیت بازیابی شود.", _state_dict(state, order)

        try:
            actions = json.loads(state.actions_json or "{}")
        except (ValueError, TypeError):
            actions = {}
        done = {int(x) for x in actions.get(str(state.floor), [])}
        message = ""
        enemy_counterattack = action in {"attack", "skill"}

        if action == "attack":
            damage = max(1, int(stats.get("attack", char.attack or 1)) + random.randint(-2, 4))
            state.enemy_hp = max(0, state.enemy_hp - damage)
            message = f"⚔️ {char.name} با حملهٔ عادی {damage} آسیب وارد کرد."
        elif action == "skill":
            if skill_id is None:
                return False, "مهارت انتخاب‌شده معتبر نیست.", _state_dict(state, order)
            learned = await session.scalar(select(CharacterSkill).where(
                CharacterSkill.character_id == char.id, CharacterSkill.skill_id == skill_id,
                CharacterSkill.unlocked.is_(True)))
            skill = await session.scalar(select(Skill).where(Skill.id == skill_id, Skill.is_active.is_(True)))
            if learned is None or skill is None:
                return False, "این مهارت را یاد نگرفته‌ای یا فعال نیست.", _state_dict(state, order)
            mana_cost = get_skill_mana_cost(skill, int(learned.level or 1))
            if char.mana < mana_cost:
                return False, f"مانای کافی نداری. هزینهٔ مهارت {mana_cost} Mana است.", _state_dict(state, order)
            char.mana -= mana_cost
            power = get_skill_power(skill, int(learned.level or 1))
            magic = int(stats.get("magic_power", char.magic_power or 0))
            damage = max(1, int(power + magic * 0.75 - max(0, state.floor * 2)))
            state.enemy_hp = max(0, state.enemy_hp - damage)
            message = f"✨ {char.name} با مهارت «{skill.name}» {damage} آسیب زد و {mana_cost} Mana مصرف کرد."
        else:
            if item_id is None:
                return False, "معجون انتخاب‌شده معتبر نیست.", _state_dict(state, order)
            row = (await session.execute(
                select(Inventory, Item).join(Item, Item.id == Inventory.item_id)
                .where(Inventory.character_id == char.id, Inventory.item_id == item_id,
                       Inventory.quantity > 0, Item.item_type == "potion").with_for_update()
            )).first()
            if row is None:
                return False, "این معجون در صندوقچهٔ شخصیتت موجود نیست.", _state_dict(state, order)
            inventory, item = row
            heal = POTION_HEAL.get(str(item.name), 0)
            if heal <= 0:
                return False, "این معجون برای مبارزه قابل استفاده نیست.", _state_dict(state, order)
            if char.hp >= max_hp:
                return False, "HP کامل است؛ معجون مصرف نشد.", _state_dict(state, order)
            ratio = 0.25 if "بزرگ" in str(item.name) else 0.10
            heal = max(int(heal), int(max_hp * ratio))
            recovered = min(heal, max_hp - char.hp)
            char.hp += recovered
            inventory.quantity -= 1
            if inventory.quantity <= 0:
                await session.delete(inventory)
            message = f"🧪 {char.name} از «{item.name}» استفاده کرد و {recovered} HP بازیابی کرد."

        done.add(telegram_id)
        actions[str(state.floor)] = sorted(done)
        if state.enemy_hp <= 0:
            message += f"\n🏆 {state.enemy_name} شکست خورد!"
            if state.floor >= state.floor_count:
                state.status = "completed"
                eligible_rewards = [mid for mid in order if all(mid in [int(x) for x in actions.get(str(f), [])] for f in range(1, state.floor_count + 1))]
                reward_gold = 500 + state.floor * 250
                for mid in eligible_rewards:
                    c = await session.scalar(select(Character).where(Character.telegram_id == mid).with_for_update())
                    if c:
                        c.gold = int(c.gold or 0) + reward_gold
                runs = (await session.execute(select(DungeonRun).where(DungeonRun.party_id == party.id, DungeonRun.status == "active"))).scalars().all()
                for run in runs:
                    run.status = "completed"
                    run.floor = state.floor
                    run.reward_gold = reward_gold if run.telegram_id in eligible_rewards else 0
                message += f"\n🎉 دانجن کامل شد؛ پاداش طلا به {len(eligible_rewards)} عضو واجدشرایط پرداخت شد."
            else:
                state.floor += 1
                state.enemy_name, state.enemy_hp = _enemy(state.dungeon_key, state.floor, len(order))
                state.enemy_max_hp = state.enemy_hp
                for run in (await session.execute(select(DungeonRun).where(DungeonRun.party_id == party.id, DungeonRun.status == "active"))).scalars().all():
                    run.floor = state.floor
                message += f"\n⬆️ طبقهٔ {state.floor} آغاز شد: {state.enemy_name}."
            state.turn_index = 0
            state.turn_started_at = now
        else:
            if enemy_counterattack:
                incoming = max(1, state.floor * 3 - int(stats.get("defense", char.defense or 0)) // 3)
                char.hp = max(0, int(char.hp or 0) - incoming)
                message += f"\n💥 ضدحملهٔ دشمن: {incoming} آسیب به {char.name}."
                if char.hp <= 0:
                    for mid in order:
                        c = await session.scalar(select(Character).where(Character.telegram_id == mid).with_for_update())
                        if c:
                            c_stats = await get_final_character_stats(mid)
                            c.max_hp = max(1, int(c_stats.get("hp", c.max_hp or 100)))
                            c.max_mana = max(1, int(c_stats.get("mana", c.max_mana or 100)))
                            c.hp = c.max_hp
                            c.mana = c.max_mana
                    state.enemy_hp = state.enemy_max_hp
                    # Keep records from already-cleared floors; only reset this floor's eligibility.
                    actions.pop(str(state.floor), None)
                    message += "\n☠️ شکست! HP/Mana همه به مقدار کامل برگشت و همین طبقه از ابتدا شروع شد؛ معجون‌های مصرف‌شده بازگردانده نمی‌شوند."
            state.turn_index = (state.turn_index + 1) % len(order)
            state.turn_started_at = now
        state.actions_json = json.dumps(actions)
        await session.commit()
        result = _state_dict(state, order)
    if eligible_rewards:
        xp_reward = 200 + (result["floor"] * 100)
        for member_id in eligible_rewards:
            await add_character_xp(member_id, xp_reward)
    return True, message, result


async def group_dungeon_attack(telegram_id: int):
    return await group_dungeon_action(telegram_id, "attack")
