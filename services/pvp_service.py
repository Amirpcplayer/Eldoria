from __future__ import annotations
from datetime import datetime, timedelta

import logging
import random
import secrets
import time
import uuid
from typing import Any

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.redis import redis

from models.character import Character
from services.title_service import sync_unlocked_titles
from models.inventory import Inventory
from models.item import Item
from models.world_systems import PvpRating, CharacterActivity

from services.combat_service import (
    get_character,
    get_character_skill,
    get_character_skills,
    has_active_battle,
)
from services.equipment_service import get_final_character_stats
from services.skill_service import get_skill_mana_cost, get_skill_power
from services.xp_service import apply_level_stats, get_required_xp


logger = logging.getLogger(__name__)

PVP_TTL = 3600
PVP_PREFIX = "eldoria:pvp_battle:"
PVP_TURN_SECONDS = 60
MIN_DAMAGE = 1

MAX_HEALS_PER_TURN = 2
MAX_HEALS_PER_BATTLE = 5

POTION_HEAL = {
    "🧪 معجون سلامتی": 5_000,
    "🧪 معجون سلامتی بزرگ": 25_000,
}

MAX_CHARACTER_LEVEL = 100


def _key(battle_id: str) -> str:
    return f"{PVP_PREFIX}{battle_id}"


def _lock_key(battle_id: str) -> str:
    return f"{PVP_PREFIX}lock:{battle_id}"


def _decode_hash(data: dict) -> dict[str, str]:
    decoded: dict[str, str] = {}

    for key, value in data.items():
        if isinstance(key, bytes):
            key = key.decode("utf-8")

        if isinstance(value, bytes):
            value = value.decode("utf-8")

        decoded[str(key)] = str(value)

    return decoded


def _as_int(data: dict, field: str, default: int = 0) -> int:
    try:
        return int(data.get(field, default))
    except (TypeError, ValueError):
        return default


def _as_float(
    data: dict,
    field: str,
    default: float = 0.0,
) -> float:
    try:
        return float(data.get(field, default))
    except (TypeError, ValueError):
        return default


async def get_pvp_battle(
    battle_id: str,
) -> dict[str, Any] | None:
    raw_data = await redis.hgetall(_key(battle_id))

    if not raw_data:
        return None

    data = _decode_hash(raw_data)

    int_fields = (
        "player1_id",
        "player2_id",
        "character1_id",
        "character2_id",
        "player1_level",
        "player2_level",
        "player1_hp",
        "player2_hp",
        "player1_max_hp",
        "player2_max_hp",
        "player1_mana",
        "player2_mana",
        "player1_max_mana",
        "player2_max_mana",
        "player1_attack",
        "player2_attack",
        "player1_magic_power",
        "player2_magic_power",
        "player1_defense",
        "player2_defense",
        "player1_magic_defense",
        "player2_magic_defense",
        "player1_speed",
        "player2_speed",
        "player1_accuracy",
        "player2_accuracy",
        "player1_critical",
        "player2_critical",
        "player1_turns",
        "player2_turns",
        "player1_heals_turn",
        "player2_heals_turn",
        "player1_heals_total",
        "player2_heals_total",
        "turn",
        "winner_id",
        "chat_id",
        "message_id",
        "reward_gold",
        "reward_xp",
        "reward_skill_xp",
    )

    for field in int_fields:
        if field in data:
            try:
                data[field] = int(data[field])
            except (TypeError, ValueError):
                return None

    data["turn_deadline"] = _as_float(data, "turn_deadline")

    for prefix in ("player1", "player2"):
        data.setdefault(f"{prefix}_heals_turn", 0)
        data.setdefault(f"{prefix}_heals_total", 0)
        data.setdefault(f"{prefix}_defending", False)

    data["player1_defending"] = (
        str(data.get("player1_defending", "0")) == "1"
    )
    data["player2_defending"] = (
        str(data.get("player2_defending", "0")) == "1"
    )
    data["finished"] = str(data.get("finished", "0")) == "1"
    data["rewarded"] = str(data.get("rewarded", "0")) == "1"
    data["battle_id"] = battle_id

    return data


async def _save_battle(battle: dict[str, Any]) -> None:
    data: dict[str, str] = {}

    for field, value in battle.items():
        if field == "battle_id":
            continue

        if isinstance(value, bool):
            data[field] = "1" if value else "0"
        else:
            data[field] = str(value)

    key = _key(str(battle["battle_id"]))

    await redis.hset(key, mapping=data)
    await redis.expire(key, PVP_TTL)

    # Persist both players' current HP/Mana as canonical profile state.
    try:
        async with AsyncSessionLocal() as session:
            for prefix in ("player1", "player2"):
                telegram_id = int(battle.get(f"{prefix}_id") or 0)
                if not telegram_id: continue
                character = await session.scalar(select(Character).where(Character.telegram_id == telegram_id).with_for_update())
                if character is None: continue
                character.hp = max(0, min(int(battle.get(f"{prefix}_hp", character.hp) or 0), int(battle.get(f"{prefix}_max_hp", character.max_hp) or character.max_hp or 100)))
                character.mana = max(0, min(int(battle.get(f"{prefix}_mana", character.mana) or 0), int(battle.get(f"{prefix}_max_mana", character.max_mana) or character.max_mana or 100)))
                character.max_hp = max(1, int(battle.get(f"{prefix}_max_hp", character.max_hp) or character.max_hp or 100))
                character.max_mana = max(1, int(battle.get(f"{prefix}_max_mana", character.max_mana) or character.max_mana or 100))
                if character.hp <= 0 and character.dead_until is None:
                    character.dead_until = datetime.utcnow() + timedelta(minutes=10)
            await session.commit()
    except Exception:
        logger.exception("Could not sync PvP HP/Mana to characters")




async def sync_character_vitals_to_pvp(telegram_id: int, hp: int, mana: int) -> None:
    """Update cached HP/Mana for a participant after a recovery action outside the PvP panel."""
    async for key in redis.scan_iter(match=f"{PVP_PREFIX}*"):
        if isinstance(key, bytes): key = key.decode("utf-8")
        if ":lock:" in str(key): continue
        raw = await redis.hgetall(key)
        if not raw: continue
        for prefix in ("player1", "player2"):
            stored = raw.get(f"{prefix}_id", 0)
            if isinstance(stored, bytes): stored = stored.decode("utf-8")
            if int(stored or 0) == int(telegram_id):
                max_hp = int(raw.get(f"{prefix}_max_hp", hp) or hp)
                max_mana = int(raw.get(f"{prefix}_max_mana", mana) or mana)
                await redis.hset(key, mapping={f"{prefix}_hp": str(min(int(hp), max_hp)), f"{prefix}_mana": str(min(int(mana), max_mana))})
                break

async def save_pvp_panel_location(
    battle_id: str,
    chat_id: int,
    message_id: int,
) -> dict[str, Any] | None:
    battle = await get_pvp_battle(battle_id)

    if battle is None:
        return None

    battle["chat_id"] = int(chat_id)
    battle["message_id"] = int(message_id)

    await _save_battle(battle)
    return battle


async def _has_active_pvp(telegram_id: int) -> bool:
    async for redis_key in redis.scan_iter(match=f"{PVP_PREFIX}*"):
        if isinstance(redis_key, bytes):
            redis_key = redis_key.decode("utf-8")

        key_text = str(redis_key)

        if ":lock:" in key_text:
            continue

        raw_data = await redis.hgetall(redis_key)

        if not raw_data:
            continue

        data = _decode_hash(raw_data)

        if data.get("finished", "0") == "1":
            continue

        player1_id = _as_int(data, "player1_id")
        player2_id = _as_int(data, "player2_id")

        if telegram_id in (player1_id, player2_id):
            return True

    return False


def _make_player_data(
    *,
    telegram_id: int,
    character: Any,
    stats: dict[str, int],
    prefix: str,
) -> dict[str, Any]:
    number = prefix[-1]

    max_hp = max(1, int(stats.get("hp", 1)))
    max_mana = max(0, int(stats.get("mana", 0)))

    return {
        f"{prefix}_id": int(telegram_id),
        f"character{number}_id": int(character.id),
        f"{prefix}_name": str(
            getattr(character, "name", None) or "قهرمان"
        ),
        f"{prefix}_level": int(
            getattr(character, "level", 1) or 1
        ),
        f"{prefix}_hp": min(max(0, int(getattr(character, "hp", max_hp) or 0)), max_hp),
        f"{prefix}_max_hp": max_hp,
        f"{prefix}_mana": min(max(0, int(getattr(character, "mana", max_mana) or 0)), max_mana),
        f"{prefix}_max_mana": max_mana,
        f"{prefix}_attack": max(0, int(stats.get("attack", 0))),
        f"{prefix}_magic_power": max(
            0, int(stats.get("magic_power", 0))
        ),
        f"{prefix}_defense": max(0, int(stats.get("defense", 0))),
        f"{prefix}_magic_defense": max(
            0, int(stats.get("magic_defense", 0))
        ),
        f"{prefix}_speed": max(0, int(stats.get("speed", 0))),
        f"{prefix}_accuracy": max(0, int(stats.get("accuracy", 0))),
        f"{prefix}_critical": max(
            0, min(100, int(stats.get("critical", 0)))
        ),
        f"{prefix}_defending": False,
        f"{prefix}_turns": 0,
        f"{prefix}_heals_turn": 0,
        f"{prefix}_heals_total": 0,
    }


async def create_pvp_battle(
    player1_id: int,
    player2_id: int,
) -> tuple[bool, str, dict[str, Any] | None]:
    if player1_id == player2_id:
        return False, "نمی‌توانی با خودت مبارزه کنی.", None
    from services.death_service import ensure_character_alive
    for telegram_id in (player1_id, player2_id):
        alive, alive_message = await ensure_character_alive(telegram_id)
        if not alive:
            return False, alive_message, None

    player1 = await get_character(player1_id)
    player2 = await get_character(player2_id)

    if player1 is None or player2 is None:
        return (
            False,
            "❌ هر دو بازیکن باید ابتدا شخصیت خود را بسازند.",
            None,
        )

    for telegram_id in (player1_id, player2_id):
        if await has_active_battle(telegram_id):
            return (
                False,
                "⚠️ یکی از بازیکنان در حال مبارزه ماجراجویی است.",
                None,
            )

        if await _has_active_pvp(telegram_id):
            return (
                False,
                "⚠️ یکی از بازیکنان در یک مبارزه PvP فعال است.",
                None,
            )

    stats1 = await get_final_character_stats(player1_id)
    stats2 = await get_final_character_stats(player2_id)

    if not stats1 or not stats2:
        return (
            False,
            "❌ دریافت مشخصات نهایی یکی از شخصیت‌ها ناموفق بود.",
            None,
        )

    battle_id = uuid.uuid4().hex[:12]
    now = time.time()

    battle: dict[str, Any] = {
        "battle_id": battle_id,
        "player1_id": int(player1_id),
        "player2_id": int(player2_id),
        "character1_id": int(player1.id),
        "character2_id": int(player2.id),
        "turn": int(player1_id),
        "turn_deadline": now + PVP_TURN_SECONDS,
        "winner_id": 0,
        "finished": False,
        "rewarded": False,
        "reward_gold": 0,
        "reward_xp": 0,
        "reward_skill_xp": 0,
    }

    battle.update(
        _make_player_data(
            telegram_id=player1_id,
            character=player1,
            stats=stats1,
            prefix="player1",
        )
    )

    battle.update(
        _make_player_data(
            telegram_id=player2_id,
            character=player2,
            stats=stats2,
            prefix="player2",
        )
    )

    await _save_battle(battle)

    return True, "مبارزه PvP شروع شد.", battle


def _player_prefix(
    battle: dict[str, Any],
    telegram_id: int,
) -> tuple[str, str] | None:
    if telegram_id == battle["player1_id"]:
        return "player1", "player2"

    if telegram_id == battle["player2_id"]:
        return "player2", "player1"

    return None


async def get_player_skills(
    battle_id: str,
    telegram_id: int,
) -> list | None:
    battle = await get_pvp_battle(battle_id)

    if battle is None or battle["finished"]:
        return None

    if telegram_id == battle["player1_id"]:
        character_id = battle["character1_id"]
    elif telegram_id == battle["player2_id"]:
        character_id = battle["character2_id"]
    else:
        return None

    return await get_character_skills(character_id)


async def get_pvp_healing_potions(
    battle_id: str,
    telegram_id: int,
) -> list[tuple[int, str, int, int]] | None:
    battle = await get_pvp_battle(battle_id)

    if battle is None or battle["finished"]:
        return None

    if telegram_id == battle["player1_id"]:
        character_id = battle["character1_id"]
    elif telegram_id == battle["player2_id"]:
        character_id = battle["character2_id"]
    else:
        return None

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Inventory, Item)
            .join(Item, Inventory.item_id == Item.id)
            .where(
                Inventory.character_id == character_id,
                Inventory.quantity > 0,
                Item.item_type == "potion",
            )
            .order_by(Item.id)
        )
        rows = result.all()

    potions: list[tuple[int, str, int, int]] = []
    prefix = "player1" if telegram_id == battle["player1_id"] else "player2"
    max_hp = int(battle.get(f"{prefix}_max_hp", 100) or 100)

    for inventory, item in rows:
        name_lower = str(item.name).lower()
        if "مانا" in name_lower or "mana" in name_lower or not any(token in name_lower for token in ("hp", "سلامتی", "health")):
            continue
        heal_amount = int(max_hp * potion_restore_ratio(item.name))

        potions.append(
            (
                int(item.id),
                str(item.name),
                int(inventory.quantity),
                int(heal_amount),
            )
        )

    return potions


def _calculate_damage(
    attack: int,
    defense: int,
    multiplier: float = 1.0,
    critical: bool = False,
) -> int:
    damage = max(MIN_DAMAGE, int(attack * multiplier - defense))

    if critical:
        damage *= 2

    return damage


def _roll_critical(critical: int) -> bool:
    chance = max(0, min(100, int(critical)))
    return chance > 0 and random.randint(1, 100) <= chance


async def _grant_winner_rewards(
    battle: dict[str, Any],
) -> dict[str, int]:
    winner_id = int(battle.get("winner_id", 0))

    if not winner_id:
        return {}

    if winner_id == battle["player1_id"]:
        loser_prefix = "player2"
    elif winner_id == battle["player2_id"]:
        loser_prefix = "player1"
    else:
        return {}

    reward_level = max(
        1,
        int(battle.get(f"{loser_prefix}_level", 1)),
    )

    gold_reward = random.randint(reward_level * 20, reward_level * 35)
    xp_reward = random.randint(reward_level * 25, reward_level * 40)
    skill_xp_reward = random.randint(
        reward_level * 10,
        reward_level * 20,
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Character)
            .where(Character.telegram_id == winner_id)
            .with_for_update()
        )
        character = result.scalar_one_or_none()

        if character is None:
            logger.error(
                "PvP winner character not found: telegram_id=%s",
                winner_id,
            )
            return {}

        character.xp = int(character.xp or 0) + xp_reward
        levels_gained = 0

        while (
            int(character.level) < MAX_CHARACTER_LEVEL
            and int(character.xp)
            >= get_required_xp(int(character.level))
        ):
            character.xp -= get_required_xp(int(character.level))
            character.level += 1
            levels_gained += 1

        if levels_gained:
            apply_level_stats(character)

        character.skill_xp = (
            int(character.skill_xp or 0) + skill_xp_reward
        )
        character.gold = int(character.gold or 0) + gold_reward
        sync_unlocked_titles(character)

        loser_id = int(battle["player2_id"] if winner_id == battle["player1_id"] else battle["player1_id"])
        winner_rating = await session.scalar(select(PvpRating).where(PvpRating.character_id == character.id).with_for_update())
        if winner_rating is None:
            winner_rating = PvpRating(character_id=character.id, rating=1000, wins=0, losses=0)
            session.add(winner_rating)
            await session.flush()
        winner_rating.rating += 20
        winner_rating.wins += 1
        winner_rating.updated_at = __import__('datetime').datetime.utcnow()
        loser = await session.scalar(select(Character).where(Character.telegram_id == loser_id).with_for_update())
        if loser is not None:
            loser_rating = await session.scalar(select(PvpRating).where(PvpRating.character_id == loser.id).with_for_update())
            if loser_rating is None:
                loser_rating = PvpRating(character_id=loser.id, rating=1000, wins=0, losses=0)
                session.add(loser_rating)
            loser_rating.rating = max(0, int(loser_rating.rating) - 10)
            loser_rating.losses += 1
            loser_rating.updated_at = __import__('datetime').datetime.utcnow()
        session.add(CharacterActivity(character_id=character.id, event_type="pvp_win", details=f"rating=+20;gold={gold_reward}"))
        if loser is not None:
            session.add(CharacterActivity(character_id=loser.id, event_type="pvp_loss", details="rating=-10"))

        await session.commit()

    return {
        "gold": gold_reward,
        "xp": xp_reward,
        "skill_xp": skill_xp_reward,
        "levels_gained": levels_gained,
    }


async def expire_pvp_turn(
    battle_id: str,
    expected_deadline: float | None = None,
) -> tuple[dict[str, Any], str] | None:
    lock_key = _lock_key(battle_id)
    token = secrets.token_hex(16)

    acquired = await redis.set(
        lock_key,
        token,
        nx=True,
        ex=15,
    )

    if not acquired:
        return None

    try:
        battle = await get_pvp_battle(battle_id)

        if battle is None or battle["finished"]:
            return None

        deadline = float(battle.get("turn_deadline", 0) or 0)

        if (
            expected_deadline is not None
            and abs(deadline - expected_deadline) > 0.01
        ):
            return None

        if deadline > time.time():
            return None

        expired_prefix = (
            "player1"
            if battle["turn"] == battle["player1_id"]
            else "player2"
        )
        next_prefix = (
            "player2"
            if expired_prefix == "player1"
            else "player1"
        )

        battle["turn"] = battle[f"{next_prefix}_id"]
        battle["turn_deadline"] = time.time() + PVP_TURN_SECONDS
        battle[f"{next_prefix}_heals_turn"] = 0

        action_text = (
            f"⌛ مهلت ۶۰ ثانیه‌ای "
            f"{battle[f'{expired_prefix}_name']} تمام شد؛ "
            f"نوبت به {battle[f'{next_prefix}_name']} رسید."
        )

        await _save_battle(battle)
        return battle, action_text

    finally:
        await redis.eval(
            """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            end
            return 0
            """,
            1,
            lock_key,
            token,
        )


async def perform_pvp_action(
    battle_id: str,
    telegram_id: int,
    action: str,
    skill_id: int | None = None,
    item_id: int | None = None,
) -> dict[str, Any]:
    if action not in {"attack", "skill", "potion", "flee"}:
        return {"ok": False, "message": "حرکت نامعتبر است."}

    lock_key = _lock_key(battle_id)
    token = secrets.token_hex(16)

    acquired = await redis.set(
        lock_key,
        token,
        nx=True,
        ex=15,
    )

    if not acquired:
        return {
            "ok": False,
            "message": "⏳ حرکت دیگری در حال پردازش است.",
        }

    try:
        battle = await get_pvp_battle(battle_id)

        if battle is None:
            return {
                "ok": False,
                "message": "❌ این مبارزه دیگر فعال نیست.",
            }

        if battle["finished"]:
            return {
                "ok": False,
                "message": "🏁 این مبارزه تمام شده است.",
            }

        pair = _player_prefix(battle, telegram_id)

        if pair is None:
            return {
                "ok": False,
                "message": "⛔ شما عضو این مبارزه نیستید.",
            }

        own, opponent = pair

        if battle["turn"] != telegram_id:
            return {
                "ok": False,
                "message": "⌛ هنوز نوبت شما نیست.",
            }

        deadline = float(battle.get("turn_deadline", 0) or 0)

        if deadline <= time.time():
            return {
                "ok": False,
                "message": "⌛ مهلت نوبت تمام شده؛ پنل را دوباره بررسی کن.",
                "timeout": True,
            }

        if (
            battle[f"{own}_hp"] <= 0
            or battle[f"{opponent}_hp"] <= 0
        ):
            return {
                "ok": False,
                "message": "این مبارزه تمام شده است.",
            }

        damage = 0
        action_text = ""
        rewards: dict[str, int] = {}

        if action == "flee":
            battle["finished"] = True
            battle["winner_id"] = battle[f"{opponent}_id"]
            action_text = (
                f"🏳️ {battle[f'{own}_name']} از مبارزه کناره‌گیری کرد."
            )

        elif action == "potion":
            if item_id is None:
                return {
                    "ok": False,
                    "message": "معجون انتخاب‌شده معتبر نیست.",
                }

            if battle[f"{own}_heals_turn"] >= MAX_HEALS_PER_TURN:
                return {
                    "ok": False,
                    "message": (
                        f"🧪 در هر نوبت فقط {MAX_HEALS_PER_TURN} "
                        "بار می‌توانی درمان شوی."
                    ),
                }

            if battle[f"{own}_heals_total"] >= MAX_HEALS_PER_BATTLE:
                return {
                    "ok": False,
                    "message": (
                        f"🧪 سقف {MAX_HEALS_PER_BATTLE} بار درمان "
                        "در این مبارزه استفاده شده است."
                    ),
                }

            missing_hp = (
                battle[f"{own}_max_hp"] - battle[f"{own}_hp"]
            )

            if missing_hp <= 0:
                return {
                    "ok": False,
                    "message": "❤️ جانت کامل است؛ معجون مصرف نشد.",
                }

            character_id = battle[f"character{own[-1]}_id"]

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Inventory, Item)
                    .join(Item, Inventory.item_id == Item.id)
                    .where(
                        Inventory.character_id == character_id,
                        Inventory.item_id == item_id,
                        Inventory.quantity > 0,
                        Item.item_type == "potion",
                    )
                    .with_for_update()
                )
                row = result.first()

                if row is None:
                    return {
                        "ok": False,
                        "message": (
                            "❌ این معجون در صندوقچه شخصیت شما موجود نیست."
                        ),
                    }

                inventory, item = row
                item_name = str(item.name)
                item_name_lower = item_name.lower()
                if potion_kind(item_name) != "hp":
                    heal_amount = None
                else:
                    heal_amount = 1

                if heal_amount is None:
                    return {
                        "ok": False,
                        "message": (
                            "❌ این معجون برای مبارزه قابل استفاده نیست."
                        ),
                    }

                max_hp = int(battle.get(f"{own}_max_hp", 100) or 100)
                heal_amount = int(max_hp * potion_restore_ratio(item_name))
                healed = min(int(heal_amount), int(missing_hp))
                inventory.quantity -= 1

                if inventory.quantity <= 0:
                    await session.delete(inventory)

                battle[f"{own}_hp"] += healed
                battle[f"{own}_heals_turn"] += 1
                battle[f"{own}_heals_total"] += 1
                battle["turn_deadline"] = time.time() + PVP_TURN_SECONDS

                await session.commit()

            action_text = (
                f"🧪 {battle[f'{own}_name']} از «{item_name}» استفاده کرد.\n"
                f"❤️ مقدار HP بازیابی‌شده: +{healed}\n"
                f"🧪 درمان این نوبت: "
                f"{battle[f'{own}_heals_turn']}/{MAX_HEALS_PER_TURN}\n"
                f"🧪 کل درمان‌ها: "
                f"{battle[f'{own}_heals_total']}/{MAX_HEALS_PER_BATTLE}\n"
                "⏳ نوبت شما ادامه دارد؛ می‌توانی معجون دیگری استفاده کنی یا حمله کنی."
            )

            await _save_battle(battle)

            return {
                "ok": True,
                "battle": battle,
                "damage": 0,
                "action_text": action_text,
                "finished": False,
                "winner_id": 0,
                "rewards": {},
                "turn_continues": True,
            }

        else:
            is_skill = action == "skill"
            attack_value = battle[f"{own}_attack"]
            defense_value = battle[f"{opponent}_defense"]
            skill_name = ""

            if is_skill:
                if skill_id is None:
                    return {
                        "ok": False,
                        "message": "شناسه مهارت نامعتبر است.",
                    }

                character_id = battle[f"character{own[-1]}_id"]
                skill_data = await get_character_skill(
                    character_id,
                    skill_id,
                )

                if skill_data is None:
                    return {
                        "ok": False,
                        "message": "این مهارت برای شخصیت شما فعال نیست.",
                    }

                skill, character_skill = skill_data
                skill_level = max(1, int(character_skill.level))
                mana_cost = int(
                    get_skill_mana_cost(skill, skill_level)
                )

                if battle[f"{own}_mana"] < mana_cost:
                    return {
                        "ok": False,
                        "message": (
                            f"🔵 مانای کافی نداری؛ "
                            f"مانای موردنیاز: {mana_cost}"
                        ),
                    }

                skill_power = int(
                    get_skill_power(skill, skill_level)
                )
                battle[f"{own}_mana"] -= mana_cost
                attack_value = (
                    battle[f"{own}_magic_power"] + skill_power
                )
                defense_value = battle[
                    f"{opponent}_magic_defense"
                ]
                skill_name = str(skill.name)

            if battle.get(f"{opponent}_defending", False):
                defense_value = int(defense_value * 1.5)
                battle[f"{opponent}_defending"] = False

            is_critical = _roll_critical(
                battle[f"{own}_critical"]
            )

            damage = _calculate_damage(
                attack=attack_value,
                defense=defense_value,
                critical=is_critical,
            )

            battle[f"{opponent}_hp"] = max(
                0,
                battle[f"{opponent}_hp"] - damage,
            )

            if is_skill:
                action_text = (
                    f"🔮 {battle[f'{own}_name']} "
                    f"از مهارت «{skill_name}» استفاده کرد."
                )
            else:
                action_text = f"⚔️ {battle[f'{own}_name']} حمله کرد."

            if is_critical:
                action_text += "\n💥 ضربه بحرانی!"

            action_text += f"\n💢 آسیب واردشده: {damage}"

            battle[f"{own}_turns"] += 1
            battle[f"{own}_heals_turn"] = 0

            if battle[f"{opponent}_hp"] <= 0:
                battle["finished"] = True
                battle["winner_id"] = battle[f"{own}_id"]
                action_text += (
                    f"\n🏆 {battle[f'{own}_name']} برنده مبارزه شد!"
                )
            else:
                battle["turn"] = battle[f"{opponent}_id"]
                battle[f"{opponent}_heals_turn"] = 0
                battle["turn_deadline"] = (
                    time.time() + PVP_TURN_SECONDS
                )

        if battle["finished"] and not battle.get("rewarded", False):
            try:
                rewards = await _grant_winner_rewards(battle)

                if rewards:
                    battle["rewarded"] = True
                    battle["reward_gold"] = rewards["gold"]
                    battle["reward_xp"] = rewards["xp"]
                    battle["reward_skill_xp"] = rewards["skill_xp"]

                    action_text += (
                        "\n\n🎁 <b>پاداش پیروزی</b>"
                        f"\n💰 طلا: +{rewards['gold']}"
                        f"\n✨ XP شخصیت: +{rewards['xp']}"
                        f"\n🔮 Skill XP: +{rewards['skill_xp']}"
                    )

                    if rewards["levels_gained"]:
                        action_text += (
                            f"\n🎉 ارتقای سطح: "
                            f"+{rewards['levels_gained']}"
                        )
                else:
                    logger.error(
                        "No PvP rewards granted for battle %s",
                        battle_id,
                    )

            except Exception:
                logger.exception(
                    "Failed to grant PvP rewards for battle %s",
                    battle_id,
                )
                action_text += (
                    "\n\n⚠️ ثبت پاداش با خطا روبه‌رو شد؛ "
                    "گزارش ربات باید بررسی شود."
                )

        await _save_battle(battle)

        return {
            "ok": True,
            "battle": battle,
            "damage": damage,
            "action_text": action_text,
            "finished": battle["finished"],
            "winner_id": battle["winner_id"],
            "rewards": rewards,
            "turn_continues": False,
        }

    finally:
        await redis.eval(
            """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            end
            return 0
            """,
            1,
            lock_key,
            token,
        )