from __future__ import annotations

import random
import uuid
import logging
import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.redis import redis

from models.adventure import AdventureArea, AdventureEnemy
from models.character import Character
from models.character_skill import CharacterSkill
from models.inventory import Inventory
from models.item import Item
from models.monster import Monster
from models.skill import Skill

from services.character_stats_service import (
    calculate_character_combat_stats,
)
from services.damage_service import (
    calculate_damage,
)
from services.monster_level_service import (
    calculate_monster_level,
)
from services.monster_stats_service import (
    calculate_monster_stats,
)
from services.quest_service import record_enemy_kill
from services.skill_service import (
    get_skill_mana_cost,
    get_skill_power,
)
from services.xp_service import add_character_xp
from services.potion_rules import potion_restore_ratio, potion_kind


logger = logging.getLogger(__name__)

BATTLE_TTL = 3600

DEFEND_MULTIPLIER = 1.5
REWARD_LOCK_TTL = 30

POTION_HEAL = {
    "🧪 معجون سلامتی": 5_000,
    "🧪 معجون سلامتی بزرگ": 25_000,
}


# ============================================================
# RANDOM MONSTER VARIANTS
# ============================================================

# وزن‌های Wolf حفظ شده‌اند.
# مجموع = 100
WOLF_VARIANT_WEIGHTS = {
    "normal_wolf": 60,
    "storm_wolf": 25,
    "alpha_wolf": 12,
    "fenrir": 3,
}


# Goblin دارای 8 Variant است.
# Variant معمولی بیشترین شانس را دارد و Boss کمترین شانس.
GOBLIN_VARIANT_WEIGHTS = {
    "goblin": 60,
    "fire_goblin": 10,
    "ice_goblin": 10,
    "goblin_archer": 8,
    "goblin_warrior": 5,
    "goblin_shaman": 3,
    "goblin_elite": 3,
    "goblin_king": 1,
}


# Golem دارای 2 Variant است.
GOLEM_VARIANT_WEIGHTS = {
    "stone_golem": 75,
    "fire_golem": 25,
}


# فقط خانواده‌هایی که واقعاً چند Variant دارند
# در حال حاضر Random Variant می‌شوند.
RANDOM_VARIANT_FAMILIES = {
    "wolf": WOLF_VARIANT_WEIGHTS,
    "goblin": GOBLIN_VARIANT_WEIGHTS,
    "golem": GOLEM_VARIANT_WEIGHTS,
}


# Fallback برای Monsterهای قدیمی یا رکوردهایی
# که family آن‌ها قابل تشخیص نیست.
VARIANT_FAMILY_MAP = {
    # Wolf
    "normal_wolf": "wolf",
    "ice_wolf": "wolf",
    "fire_wolf": "wolf",
    "water_wolf": "wolf",
    "storm_wolf": "wolf",
    "shadow_wolf": "wolf",
    "blood_wolf": "wolf",
    "steel_wolf": "wolf",
    "alpha_wolf": "wolf",
    "fenrir": "wolf",

    # Goblin
    "goblin": "goblin",
    "fire_goblin": "goblin",
    "ice_goblin": "goblin",
    "goblin_archer": "goblin",
    "goblin_warrior": "goblin",
    "goblin_shaman": "goblin",
    "goblin_elite": "goblin",
    "goblin_king": "goblin",

    # Golem
    "stone_golem": "golem",
    "fire_golem": "golem",
}


def get_monster_variant(
    monster: Monster,
) -> str | None:
    return getattr(
        monster,
        "variant",
        None,
    )


def get_monster_family(
    monster: Monster,
) -> str | None:

    # اولویت با family واقعی دیتابیس است.
    family = getattr(
        monster,
        "family",
        None,
    )

    if family:
        return str(family)

    # Fallback برای رکوردهای قدیمی.
    variant = get_monster_variant(
        monster
    )

    if not variant:
        return None

    return VARIANT_FAMILY_MAP.get(
        variant
    )


def choose_random_variant(
    family: str,
) -> str | None:

    variant_weights = RANDOM_VARIANT_FAMILIES.get(
        family
    )

    if not variant_weights:
        return None

    variants = list(
        variant_weights.keys()
    )

    weights = list(
        variant_weights.values()
    )

    return random.choices(
        variants,
        weights=weights,
        k=1,
    )[0]


async def get_random_variant_monster(
    base_monster: Monster,
) -> Monster:

    family = get_monster_family(
        base_monster
    )

    # اگر خانواده چند Variant نداشته باشد،
    # همان Monster اصلی استفاده می‌شود.
    if family not in RANDOM_VARIANT_FAMILIES:
        return base_monster

    variant = choose_random_variant(
        family
    )

    if variant is None:
        return base_monster

    async with AsyncSessionLocal() as session:

        monster = await session.scalar(
            select(Monster).where(
                Monster.variant == variant,
                Monster.family == family,
                Monster.is_active.is_(True),
            )
        )

        if monster is None:
            return base_monster

        return monster


# ============================================================
# REDIS KEYS
# ============================================================

def get_battle_key(
    battle_id: str,
) -> str:
    return f"eldoria:battle:{battle_id}"


def get_reward_lock_key(
    battle_id: str,
) -> str:
    return f"eldoria:battle_reward:{battle_id}"


# ============================================================
# BATTLE STORAGE
# ============================================================

async def get_battle(
    battle_id: str,
) -> dict[str, Any] | None:

    data = await redis.hgetall(
        get_battle_key(battle_id)
    )

    if not data:
        return None

    int_fields = {
        "telegram_id",
        "character_id",
        "enemy_id",
        "monster_id",
        "enemy_level",
        "enemy_hp",
        "enemy_max_hp",
        "enemy_attack",
        "enemy_magic_power",
        "enemy_defense",
        "enemy_magic_defense",
        "enemy_speed",
        "enemy_accuracy",
        "enemy_luck",
        "enemy_critical",
        "enemy_xp",
        "enemy_skill_xp",
        "enemy_gold",
        "player_level",
        "player_hp",
        "player_max_hp",
        "player_attack",
        "player_magic_power",
        "player_defense",
        "player_magic_defense",
        "player_mana",
        "player_max_mana",
        "player_speed",
        "player_accuracy",
        "player_luck",
        "player_critical",
        "turn",
    }

    for field in int_fields:
        if field in data:
            data[field] = int(
                data[field]
            )

    float_fields = {
        "enemy_fire_resistance",
        "enemy_water_resistance",
        "enemy_ice_resistance",
        "enemy_earth_resistance",
        "enemy_wind_resistance",
        "enemy_electro_resistance",
        "enemy_shadow_resistance",
        "enemy_light_resistance",
        "enemy_blood_resistance",
        "enemy_steel_resistance",
    }

    for field in float_fields:
        if field in data:
            data[field] = float(
                data[field]
            )

    if "defending" in data:
        data["defending"] = (
            data["defending"] == "1"
        )

    data["battle_id"] = battle_id

    return data


async def save_battle(
    battle: dict[str, Any],
) -> None:

    battle_id = battle["battle_id"]

    data = {}

    for key, value in battle.items():

        if key == "battle_id":
            continue

        if isinstance(value, bool):
            data[key] = (
                "1"
                if value
                else "0"
            )
        else:
            data[key] = str(value)

    key = get_battle_key(
        battle_id
    )

    await redis.hset(
        key,
        mapping=data,
    )

    await redis.expire(
        key,
        BATTLE_TTL,
    )

    # Keep the canonical character HP/Mana in PostgreSQL in sync with battle state.
    try:
        telegram_id = int(battle.get("telegram_id") or 0)
        if telegram_id:
            async with AsyncSessionLocal() as session:
                character = await session.scalar(select(Character).where(Character.telegram_id == telegram_id).with_for_update())
                if character is not None:
                    character.hp = max(0, min(int(battle.get("player_hp", character.hp) or 0), int(battle.get("player_max_hp", character.max_hp) or character.max_hp or 100)))
                    character.mana = max(0, min(int(battle.get("player_mana", character.mana) or 0), int(battle.get("player_max_mana", character.max_mana) or character.max_mana or 100)))
                    character.max_hp = max(1, int(battle.get("player_max_hp", character.max_hp) or character.max_hp or 100))
                    character.max_mana = max(1, int(battle.get("player_max_mana", character.max_mana) or character.max_mana or 100))
                    if character.hp <= 0 and character.dead_until is None:
                        character.dead_until = datetime.utcnow() + timedelta(minutes=10)
                    await session.commit()
    except Exception:
        logger.exception("Could not sync adventure battle HP/Mana to character row")




async def sync_character_vitals_to_battles(telegram_id: int, hp: int, mana: int) -> None:
    """Update an active Adventure battle cache after an out-of-panel recovery action."""
    async for key in redis.scan_iter(match="eldoria:battle:*"):
        if isinstance(key, bytes): key = key.decode("utf-8")
        if str(key).startswith("eldoria:battle_reward:"): continue
        raw = await redis.hgetall(key)
        if not raw: continue
        stored = raw.get("telegram_id", 0)
        if isinstance(stored, bytes): stored = stored.decode("utf-8")
        if int(stored or 0) != int(telegram_id): continue
        max_hp = int(raw.get("player_max_hp", hp) or hp)
        max_mana = int(raw.get("player_max_mana", mana) or mana)
        await redis.hset(key, mapping={"player_hp": str(min(int(hp), max_hp)), "player_mana": str(min(int(mana), max_mana))})

async def delete_battle(
    battle_id: str,
) -> None:

    await redis.delete(
        get_battle_key(
            battle_id
        )
    )


# ============================================================
# CHARACTER / ENEMY
# ============================================================

async def get_character(
    telegram_id: int,
) -> Character | None:

    async with AsyncSessionLocal() as session:

        return await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )


async def get_enemy(
    enemy_id: int,
) -> AdventureEnemy | None:

    async with AsyncSessionLocal() as session:

        return await session.scalar(
            select(AdventureEnemy).where(
                AdventureEnemy.id == enemy_id,
                AdventureEnemy.is_active.is_(True),
            )
        )


async def get_enemy_combat_data(
    enemy_id: int,
) -> tuple[
    AdventureEnemy | None,
    Monster | None,
    AdventureArea | None,
]:

    async with AsyncSessionLocal() as session:

        enemy = await session.scalar(
            select(AdventureEnemy).where(
                AdventureEnemy.id == enemy_id,
                AdventureEnemy.is_active.is_(True),
            )
        )

        if enemy is None:
            return None, None, None

        if enemy.monster_id is None:
            return enemy, None, None

        monster = await session.scalar(
            select(Monster).where(
                Monster.id == enemy.monster_id,
                Monster.is_active.is_(True),
            )
        )

        if monster is None:
            return enemy, None, None

        area = await session.scalar(
            select(AdventureArea).where(
                AdventureArea.id == enemy.area_id,
                AdventureArea.is_active.is_(True),
            )
        )

        return (
            enemy,
            monster,
            area,
        )


# ============================================================
# CHARACTER SKILLS
# ============================================================

async def get_character_skills(
    character_id: int,
) -> list[
    tuple[Skill, CharacterSkill]
]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(
                Skill,
                CharacterSkill,
            )
            .join(
                CharacterSkill,
                CharacterSkill.skill_id == Skill.id,
            )
            .where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.unlocked.is_(True),
                CharacterSkill.slot.is_not(None),
                Skill.is_active.is_(True),
            )
            .order_by(
                CharacterSkill.slot,
                Skill.id,
            )
        )

        return list(
            result.all()
        )


async def get_character_skill(
    character_id: int,
    skill_id: int,
) -> tuple[
    Skill,
    CharacterSkill,
] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(
                Skill,
                CharacterSkill,
            )
            .join(
                CharacterSkill,
                CharacterSkill.skill_id == Skill.id,
            )
            .where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == skill_id,
                CharacterSkill.unlocked.is_(True),
                CharacterSkill.slot.is_not(None),
                Skill.is_active.is_(True),
            )
        )

        return result.first()


# ============================================================
# ACTIVE BATTLE
# ============================================================

async def has_active_battle(
    telegram_id: int,
) -> bool:

    async for key in redis.scan_iter(
        match="eldoria:battle:*"
    ):

        if isinstance(key, bytes):
            key = key.decode(
                "utf-8"
            )

        if key.startswith(
            "eldoria:battle_reward:"
        ):
            continue

        data = await redis.hgetall(
            key
        )

        if not data:
            continue

        stored_telegram_id = data.get(
            "telegram_id",
            0,
        )

        if isinstance(
            stored_telegram_id,
            bytes,
        ):
            stored_telegram_id = (
                stored_telegram_id.decode(
                    "utf-8"
                )
            )

        if int(
            stored_telegram_id
        ) != telegram_id:
            continue

        return True

    return False


# ============================================================
# MONSTER HELPERS
# ============================================================

def get_monster_resistance(
    battle: dict[str, Any],
    attack_element: str,
) -> float:

    attack_element = (
        attack_element.lower()
    )

    resistance_map = {
        "fire": "enemy_fire_resistance",
        "water": "enemy_water_resistance",
        "ice": "enemy_ice_resistance",
        "earth": "enemy_earth_resistance",
        "wind": "enemy_wind_resistance",
        "electro": "enemy_electro_resistance",
        "shadow": "enemy_shadow_resistance",
        "light": "enemy_light_resistance",
        "blood": "enemy_blood_resistance",
        "steel": "enemy_steel_resistance",
    }

    field = resistance_map.get(
        attack_element
    )

    if field is None:
        return 0.0

    return float(
        battle.get(
            field,
            0.0,
        )
    )


def roll_critical(
    critical: int,
) -> bool:

    critical = max(
        0,
        min(
            critical,
            100,
        ),
    )

    if critical <= 0:
        return False

    return (
        random.randint(
            1,
            100,
        )
        <= critical
    )


# ============================================================
# CREATE BATTLE
# ============================================================

async def create_battle(
    telegram_id: int,
    enemy_id: int,
) -> tuple[
    bool,
    str,
    dict[str, Any] | None,
]:

    from services.death_service import ensure_character_alive
    alive, alive_message = await ensure_character_alive(telegram_id)
    if not alive:
        return False, alive_message, None

    if await has_active_battle(
        telegram_id
    ):
        return (
            False,
            "⚔️ تو در حال حاضر در یک مبارزه هستی.",
            None,
        )

    character = await get_character(
        telegram_id
    )

    if character is None:
        return (
            False,
            "❌ قهرمان پیدا نشد.",
            None,
        )

    (
        enemy,
        base_monster,
        area,
    ) = await get_enemy_combat_data(
        enemy_id
    )

    if enemy is None:
        return (
            False,
            "❌ دشمن پیدا نشد.",
            None,
        )

    if base_monster is None:
        return (
            False,
            "❌ اطلاعات هیولای این دشمن کامل نیست.",
            None,
        )

    if area is None:
        return (
            False,
            "❌ منطقه این دشمن پیدا نشد.",
            None,
        )

    if character.level < area.min_level:
        return (
            False,
            (
                f"🔒 برای ورود به این منطقه "
                f"حداقل Level {area.min_level} لازم است."
            ),
            None,
        )

    # --------------------------------------------------------
    # RANDOM VARIANT
    # --------------------------------------------------------

    # برای Wolf / Goblin / Golem:
    # Variant به صورت تصادفی انتخاب می‌شود.
    #
    # برای خانواده‌های تک‌Variant:
    # همان Monster اصلی برگردانده می‌شود.
    monster = await get_random_variant_monster(
        base_monster
    )

    effective_level = calculate_monster_level(
        character_level=character.level,
        enemy_level=enemy.level,
        area_min_level=area.min_level,
        area_max_level=area.max_level,
    )

    monster_stats = calculate_monster_stats(
        monster,
        effective_level,
    )

    character_stats = (
        await calculate_character_combat_stats(
            character
        )
    )

    battle_id = str(
        uuid.uuid4()
    )

    monster_variant = (
        get_monster_variant(
            monster
        )
    )

    monster_element = getattr(
        monster,
        "element",
        None,
    )

    if not monster_element:
        monster_element = "neutral"

    battle = {
        "battle_id": battle_id,

        "telegram_id": telegram_id,
        "character_id": character.id,

        # AdventureEnemy اصلی
        "enemy_id": enemy.id,

        # Monster واقعی انتخاب‌شده برای این مبارزه
        "monster_id": monster.id,
        "enemy_variant": (
            monster_variant
            or "default"
        ),

        "enemy_level": effective_level,

        "enemy_hp": monster_stats.hp,
        "enemy_max_hp": monster_stats.hp,

        "enemy_attack": monster_stats.attack,
        "enemy_magic_power": monster_stats.magic_power,
        "enemy_defense": monster_stats.defense,
        "enemy_magic_defense": monster_stats.magic_defense,
        "enemy_speed": monster_stats.speed,
        "enemy_accuracy": monster_stats.accuracy,
        "enemy_luck": monster_stats.luck,
        "enemy_critical": monster_stats.critical,

        "enemy_xp": enemy.xp_reward,
        "enemy_skill_xp": getattr(
            enemy,
            "skill_xp_reward",
            0,
        ),
        "enemy_gold": enemy.gold_reward,

        "enemy_element": monster_element,

        "enemy_fire_resistance": getattr(
            monster,
            "fire_resistance",
            0.0,
        ),
        "enemy_water_resistance": getattr(
            monster,
            "water_resistance",
            0.0,
        ),
        "enemy_ice_resistance": getattr(
            monster,
            "ice_resistance",
            0.0,
        ),
        "enemy_earth_resistance": getattr(
            monster,
            "earth_resistance",
            0.0,
        ),
        "enemy_wind_resistance": getattr(
            monster,
            "wind_resistance",
            0.0,
        ),
        "enemy_electro_resistance": getattr(
            monster,
            "electro_resistance",
            0.0,
        ),
        "enemy_shadow_resistance": getattr(
            monster,
            "shadow_resistance",
            0.0,
        ),
        "enemy_light_resistance": getattr(
            monster,
            "light_resistance",
            0.0,
        ),
        "enemy_blood_resistance": getattr(
            monster,
            "blood_resistance",
            0.0,
        ),
        "enemy_steel_resistance": getattr(
            monster,
            "steel_resistance",
            0.0,
        ),

        "player_level": character.level,

        "player_hp": min(max(0, int(character.hp or 0)), int(character_stats.hp)),
        "player_max_hp": character_stats.hp,

        "player_attack": character_stats.attack,
        "player_magic_power": character_stats.magic_power,
        "player_defense": character_stats.defense,
        "player_magic_defense": character_stats.magic_defense,
        "player_mana": min(max(0, int(character.mana or 0)), int(character_stats.mana)),
        "player_max_mana": character_stats.mana,
        "player_speed": character_stats.speed,
        "player_accuracy": character_stats.accuracy,
        "player_luck": character_stats.luck,
        "player_critical": character_stats.critical,

        "turn": 1,
        "defending": False,
    }

    await save_battle(
        battle
    )

    variant_name = (
        monster_variant
        or monster.name
    )

    return (
        True,
        (
            f"⚔️ مبارزه آغاز شد!\n\n"
            f" {monster.name}\n"
            f"⭐ Level {effective_level}\n"
            f"🧬 Variant: {variant_name}"
        ),
        battle,
    )


# ============================================================
# PLAYER NORMAL ATTACK
# ============================================================

async def player_attack(
    battle_id: str,
) -> tuple[
    bool,
    int,
    bool,
    dict[str, Any] | None,
]:

    battle = await get_battle(
        battle_id
    )

    if battle is None:
        return (
            False,
            0,
            False,
            None,
        )

    if battle["enemy_hp"] <= 0:
        return (
            False,
            0,
            True,
            battle,
        )

    if battle["player_hp"] <= 0:
        return (
            False,
            0,
            False,
            battle,
        )

    battle["defending"] = False

    is_critical = roll_critical(
        battle["player_critical"]
    )

    result = calculate_damage(
        attack=battle["player_attack"],
        defense=battle["enemy_defense"],
        skill_power=1.0,
        attack_element="neutral",
        defender_element=battle.get(
            "enemy_element",
            "neutral",
        ),
        resistance=0.0,
        critical=is_critical,
        randomize=True,
    )

    damage = result.damage
    try:
        from services.scroll_service import has_buff
        if await has_buff(int(battle["telegram_id"]), "power"):
            damage = int(damage * 1.20)
    except Exception:
        logger.exception("Could not apply power scroll to normal attack")

    battle["enemy_hp"] = max(
        0,
        battle["enemy_hp"] - damage,
    )

    battle["turn"] += 1

    await save_battle(
        battle
    )

    return (
        True,
        damage,
        battle["enemy_hp"] <= 0,
        battle,
    )


# ============================================================
# PLAYER SKILL
# ============================================================

async def player_skill(
    battle_id: str,
    skill_id: int,
) -> tuple[
    bool,
    str,
    int,
    bool,
    dict[str, Any] | None,
]:

    battle = await get_battle(
        battle_id
    )

    if battle is None:
        return (
            False,
            "❌ مبارزه فعال نیست.",
            0,
            False,
            None,
        )

    if battle["enemy_hp"] <= 0:
        return (
            False,
            "❌ این مبارزه تمام شده است.",
            0,
            True,
            battle,
        )

    if battle["player_hp"] <= 0:
        return (
            False,
            "❌ قهرمان شکست خورده است.",
            0,
            False,
            battle,
        )

    skill_data = await get_character_skill(
        battle["character_id"],
        skill_id,
    )

    if skill_data is None:
        return (
            False,
            "❌ این مهارت در دسترس نیست.",
            0,
            False,
            battle,
        )

    skill, character_skill = skill_data

    skill_level = character_skill.level

    mana_cost = get_skill_mana_cost(
        skill,
        skill_level,
    )

    if battle["player_mana"] < mana_cost:
        return (
            False,
            (
                f"🔵 مانای کافی نداری.\n"
                f"نیاز: {mana_cost}"
            ),
            0,
            False,
            battle,
        )

    skill_power = get_skill_power(
        skill,
        skill_level,
    )

    skill_multiplier = max(
        0.1,
        skill_power / 100.0,
    )

    battle["player_mana"] -= mana_cost

    attack_element = (
        skill.element.lower()
        if skill.element
        else "neutral"
    )

    resistance = get_monster_resistance(
        battle,
        attack_element,
    )
    try:
        from services.scroll_service import has_buff
        if await has_buff(int(battle["telegram_id"]), "resistance"):
            resistance = 0.0
    except Exception:
        logger.exception("Could not apply resistance scroll")

    is_critical = roll_critical(
        battle["player_critical"]
    )

    result = calculate_damage(
        attack=battle["player_magic_power"],
        defense=battle["enemy_magic_defense"],
        skill_power=skill_multiplier,
        attack_element=attack_element,
        defender_element=battle.get(
            "enemy_element",
            "neutral",
        ),
        resistance=resistance,
        critical=is_critical,
        randomize=True,
    )

    damage = result.damage
    try:
        from services.scroll_service import has_buff
        if await has_buff(int(battle["telegram_id"]), "power"):
            damage = int(damage * 1.20)
    except Exception:
        logger.exception("Could not apply power scroll to magic attack")

    battle["enemy_hp"] = max(
        0,
        battle["enemy_hp"] - damage,
    )

    battle["defending"] = False
    battle["turn"] += 1

    await save_battle(
        battle
    )

    return (
        True,
        f"✨ {skill.name}",
        damage,
        battle["enemy_hp"] <= 0,
        battle,
    )


# ============================================================
# PLAYER DEFEND
# ============================================================

async def player_defend(
    battle_id: str,
) -> tuple[
    bool,
    dict[str, Any] | None,
]:

    battle = await get_battle(
        battle_id
    )

    if battle is None:
        return False, None

    if battle["enemy_hp"] <= 0:
        return False, battle

    if battle["player_hp"] <= 0:
        return False, battle

    battle["defending"] = True
    battle["turn"] += 1

    await save_battle(
        battle
    )

    return (
        True,
        battle,
    )


# ============================================================
# POTIONS
# ============================================================

async def get_healing_potions(
    character_id: int,
    max_hp: int | None = None,
) -> list[
    tuple[Inventory, Item, int]
]:

    async with AsyncSessionLocal() as session:
        if max_hp is None:
            character = await session.scalar(select(Character).where(Character.id == character_id))
            max_hp = int(getattr(character, "max_hp", 100) or 100)

        result = await session.execute(
            select(
                Inventory,
                Item,
            )
            .join(
                Item,
                Inventory.item_id == Item.id,
            )
            .where(
                Inventory.character_id == character_id,
                Inventory.quantity > 0,
                Item.item_type == "potion",
            )
            .order_by(
                Inventory.id
            )
        )

        potions = []

        for inventory_item, item in result.all():

            name = str(item.name).lower()
            if "مانا" in name or "mana" in name or not any(token in name for token in ("hp", "سلامتی", "health")):
                continue
            heal_amount = int(max(1, max_hp) * potion_restore_ratio(item.name))

            potions.append(
                (
                    inventory_item,
                    item,
                    heal_amount,
                )
            )

        return potions


async def use_healing_potion(
    battle_id: str,
    item_id: int,
) -> tuple[
    bool,
    str,
    int,
    dict[str, Any] | None,
]:

    battle = await get_battle(
        battle_id
    )

    if battle is None:
        return (
            False,
            "❌ مبارزه فعال نیست.",
            0,
            None,
        )

    if battle["player_hp"] <= 0:
        return (
            False,
            "❌ قهرمان شکست خورده است.",
            0,
            battle,
        )

    if battle["player_hp"] >= battle["player_max_hp"]:
        return (
            False,
            "❤️ سلامتی تو کامل است.",
            0,
            battle,
        )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(
                Inventory,
                Item,
            )
            .join(
                Item,
                Inventory.item_id == Item.id,
            )
            .where(
                Inventory.character_id
                == battle["character_id"],
                Inventory.item_id == item_id,
                Inventory.quantity > 0,
                Item.item_type == "potion",
            )
        )

        row = result.first()

        if row is None:
            return (
                False,
                "❌ این معجون را نداری.",
                0,
                battle,
            )

        inventory_item, item = row

        name_lower = str(item.name).lower()
        if potion_kind(item.name) != "hp":
            heal_amount = 0
        else:
            heal_amount = 1

        if heal_amount <= 0:
            return (
                False,
                "❌ این آیتم یک معجون درمانی نیست.",
                0,
                battle,
            )

        max_hp = int(battle["player_max_hp"] or 100)
        heal_amount = int(max_hp * potion_restore_ratio(item.name))
        try:
            from services.scroll_service import has_buff
            if await has_buff(int(battle["telegram_id"]), "healing"):
                heal_amount = int(heal_amount * 1.20)
        except Exception:
            logger.exception("Could not apply healing scroll")
        actual_heal = min(heal_amount, max_hp - int(battle["player_hp"]))

        battle["player_hp"] += actual_heal

        inventory_item.quantity -= 1

        await session.commit()

    await save_battle(
        battle
    )

    return (
        True,
        f"🧪 {item.name} مصرف شد.",
        actual_heal,
        battle,
    )


# ============================================================
# ENEMY TURN
# ============================================================

async def enemy_turn(
    battle_id: str,
) -> tuple[
    bool,
    int,
    bool,
    dict[str, Any] | None,
]:

    battle = await get_battle(
        battle_id
    )

    if battle is None:
        return (
            False,
            0,
            False,
            None,
        )

    if battle["enemy_hp"] <= 0:
        return (
            False,
            0,
            False,
            battle,
        )

    if battle["player_hp"] <= 0:
        return (
            False,
            0,
            True,
            battle,
        )

    defense = battle["player_defense"]

    if battle.get(
        "defending",
        False,
    ):
        defense = int(
            defense * DEFEND_MULTIPLIER
        )

    attack_element = battle.get(
        "enemy_element",
        "neutral",
    )

    is_critical = roll_critical(
        battle.get(
            "enemy_critical",
            0,
        )
    )

    result = calculate_damage(
        attack=battle["enemy_attack"],
        defense=defense,
        skill_power=1.0,
        attack_element=attack_element,
        defender_element="neutral",
        resistance=0.0,
        critical=is_critical,
        randomize=True,
    )

    damage = result.damage
    try:
        from services.scroll_service import has_buff
        if await has_buff(int(battle["telegram_id"]), "defense"):
            damage = int(damage * 0.80)
    except Exception:
        logger.exception("Could not apply defense scroll")

    battle["player_hp"] = max(
        0,
        battle["player_hp"] - damage,
    )

    battle["defending"] = False

    await save_battle(
        battle
    )

    return (
        True,
        damage,
        battle["player_hp"] <= 0,
        battle,
    )


# ============================================================
# VICTORY / REWARDS
# ============================================================

async def finish_victory(
    battle_id: str,
) -> tuple[
    bool,
    int,
    int,
    int,
    int,
]:

    battle = await get_battle(
        battle_id
    )

    if battle is None:
        return (
            False,
            0,
            0,
            0,
            0,
        )

    if battle["enemy_hp"] > 0:
        return (
            False,
            0,
            0,
            0,
            0,
        )

    telegram_id = battle[
        "telegram_id"
    ]

    reward_lock_key = (
        get_reward_lock_key(
            battle_id
        )
    )

    locked = await redis.set(
        reward_lock_key,
        "1",
        nx=True,
        ex=REWARD_LOCK_TTL,
    )

    if not locked:
        return (
            False,
            0,
            0,
            0,
            0,
        )

    xp_reward = battle[
        "enemy_xp"
    ]

    skill_xp_reward = battle[
        "enemy_skill_xp"
    ]

    gold_reward = battle[
        "enemy_gold"
    ]
    try:
        from services.scroll_service import has_buff
        explorer_active = await has_buff(int(telegram_id), "explorer")
    except Exception:
        explorer_active = False
    if explorer_active:
        xp_reward = int(xp_reward * 1.30)
        skill_xp_reward = int(skill_xp_reward * 1.30)
        gold_reward = int(gold_reward * 1.30)

    try:

        (
            success,
            current_xp,
            new_level,
            levels_gained,
        ) = await add_character_xp(
            telegram_id,
            xp_reward,
        )

        if not success:

            await redis.delete(
                reward_lock_key
            )

            return (
                False,
                0,
                0,
                0,
                0,
            )

        async with AsyncSessionLocal() as session:

            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id
                    == telegram_id
                )
            )

            if character is None:

                await redis.delete(
                    reward_lock_key
                )

                return (
                    False,
                    0,
                    0,
                    0,
                    0,
                )

            character.skill_xp += (
                skill_xp_reward
            )

            character.gold += (
                gold_reward
            )

            await session.commit()

        try:
            await record_enemy_kill(
                telegram_id,
                battle["enemy_id"],
            )
        except Exception:
            pass

        # دفترچهٔ هیولاها، مأموریت روزانه و دراپ متریال‌ها از پیروزی واقعی
        # تغذیه می‌شوند؛ قفل پاداش بالا مانع ثبت چندبارهٔ همین پیروزی است.
        drops = []
        try:
            from services.world_progression_service import record_kill_and_drop
            drops = await record_kill_and_drop(
                telegram_id,
                battle.get("monster_id"),
                battle.get("enemy_variant"),
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Could not record progression/drop rewards")
        # Consumed by the victory panel immediately after finish_victory returns.
        await redis.set(f"eldoria:last_adventure_drops:{telegram_id}", json.dumps(drops, ensure_ascii=False), ex=300)

        await delete_battle(
            battle_id
        )

        await redis.delete(
            reward_lock_key
        )

        return (
            True,
            xp_reward,
            skill_xp_reward,
            gold_reward,
            levels_gained,
        )

    except Exception:

        await redis.delete(
            reward_lock_key
        )

        raise


# ============================================================
# BATTLE CLEANUP
# ============================================================

async def finish_battle(
    battle_id: str,
) -> None:

    await delete_battle(
        battle_id
    )

    await redis.delete(
        get_reward_lock_key(
            battle_id
        )
    )


async def flee_battle(
    battle_id: str,
) -> bool:

    battle = await get_battle(
        battle_id
    )

    if battle is None:
        return False

    await delete_battle(
        battle_id
    )

    await redis.delete(
        get_reward_lock_key(
            battle_id
        )
    )

    return True