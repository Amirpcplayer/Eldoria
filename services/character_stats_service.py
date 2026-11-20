from __future__ import annotations

from dataclasses import dataclass

from models.character import Character
from services.equipment_service import get_equipped_equipments
from services.power_service import get_hero_base_stats
from models.social_systems import CharacterPet, Pet
from sqlalchemy import select
from database.database import AsyncSessionLocal


@dataclass(frozen=True)
class CharacterCombatStats:
    hp: int
    max_hp: int
    mana: int
    max_mana: int

    attack: int
    magic_power: int

    defense: int
    magic_defense: int

    speed: int
    accuracy: int
    luck: int
    critical: int


def calculate_character_base_stats(
    character: Character,
) -> CharacterCombatStats:
    stats = get_hero_base_stats(
        character.level,
    )

    return CharacterCombatStats(
        hp=stats.hp,
        max_hp=stats.hp,
        mana=stats.mana,
        max_mana=stats.mana,
        attack=stats.attack,
        magic_power=stats.magic_power,
        defense=stats.defense,
        magic_defense=stats.magic_defense,
        speed=stats.speed,
        accuracy=stats.accuracy,
        luck=stats.luck,
        critical=stats.critical,
    )


async def calculate_character_combat_stats(
    character: Character,
) -> CharacterCombatStats:
    base = calculate_character_base_stats(
        character,
    )

    # مهم: get_equipped_equipments شناسه تلگرام می‌خواهد،
    # نه شناسه داخلی Character.
    equipped_items = await get_equipped_equipments(
        int(character.telegram_id),
    )

    bonuses = {
        "attack": 0,
        "magic_power": 0,
        "defense": 0,
        "magic_defense": 0,
        "hp": 0,
        "mana": 0,
        "speed": 0,
        "accuracy": 0,
        "critical": 0,
    }

    rarity_multipliers = {
        "common": 1, "uncommon": 3, "rare": 10, "epic": 30,
        "legendary": 80, "mythic": 180, "divine": 350,
    }
    utility_multipliers = {
        "common": 1.0, "uncommon": 1.1, "rare": 1.25, "epic": 1.5,
        "legendary": 2.0, "mythic": 2.5, "divine": 3.0,
    }
    for character_equipment, equipment in equipped_items:
        enhancement_level = int(getattr(character_equipment, "enhancement_level", 0) or 0)
        rarity = str(getattr(equipment, "rarity", "common") or "common").lower()
        rarity_multiplier = rarity_multipliers.get(rarity, 1)
        for stat in bonuses:
            raw = int(getattr(equipment, stat, 0) or 0)
            if raw:
                # Main combat stats scale dramatically with rarity; utility stats
                # use a gentler curve so divine gear does not grant absurd speed,
                # accuracy or thousands of percent critical chance.
                multiplier = utility_multipliers.get(rarity, 1.0) if stat in {"speed", "accuracy", "critical"} else rarity_multiplier
                raw = int(raw * multiplier)
                raw += int(raw * 0.05 * enhancement_level)
            bonuses[stat] += raw

    # پاداش ست‌ها در همین سرویس مرکزی اعمال می‌شود تا پروفایل، PvP،
    # دانجن و مبارزه همگی دقیقاً از محاسبهٔ یکسان استفاده کنند.
    set_counts: dict[str, int] = {}
    for _character_equipment, equipment in equipped_items:
        set_key = getattr(equipment, "set_key", None)
        if set_key:
            set_counts[str(set_key)] = set_counts.get(str(set_key), 0) + 1

    set_bonuses = {
        "eldoria_guardian": {
            2: {"defense": 10, "magic_defense": 5, "hp": 80},
            4: {"defense": 20, "magic_defense": 15, "hp": 180},
            6: {"defense": 30, "magic_defense": 25, "hp": 300},
        },
        "arcane_storm": {
            2: {"magic_power": 12, "mana": 50},
            4: {"magic_power": 25, "mana": 120, "magic_defense": 10},
            6: {"magic_power": 40, "mana": 200, "critical": 5},
        },
        "dragon_emperor": {
            2: {"attack": 12, "defense": 8},
            4: {"attack": 25, "defense": 18, "hp": 150},
            6: {"attack": 45, "defense": 30, "critical": 8},
        },
        "moonshadow": {
            2: {"speed": 8, "accuracy": 5},
            4: {"speed": 16, "accuracy": 10, "critical": 5},
            6: {"speed": 25, "accuracy": 15, "critical": 10, "attack": 15},
        },
        "astral_vanguard": {
            2: {"defense": 2500, "magic_defense": 1500, "hp": 25000},
            4: {"defense": 7000, "magic_defense": 5000, "hp": 70000},
            6: {"defense": 14000, "magic_defense": 10000, "hp": 150000},
        },
        "void_archmage": {
            2: {"magic_power": 2500, "mana": 25000, "magic_defense": 1500},
            4: {"magic_power": 7000, "mana": 70000, "magic_defense": 5000},
            6: {"magic_power": 14000, "mana": 150000, "magic_defense": 10000},
        },
        "dragon_overlord_endgame": {
            2: {"attack": 2500, "defense": 1500, "hp": 25000},
            4: {"attack": 7000, "defense": 5000, "hp": 70000},
            6: {"attack": 14000, "defense": 10000, "hp": 150000, "critical": 10},
        },
        "divine_eldoria": {
            2: {"attack": 50000, "defense": 40000, "hp": 100000, "magic_defense": 40000},
            4: {"attack": 250000, "defense": 180000, "hp": 350000, "magic_defense": 180000, "magic_power": 200000},
            6: {"attack": 650000, "defense": 450000, "hp": 700000, "magic_defense": 450000, "magic_power": 500000, "critical": 15},
        },
    }
    for set_key, count in set_counts.items():
        tiers = set_bonuses.get(set_key, {})
        # بالاترین آستانهٔ تکمیل‌شده اعمال می‌شود؛ پاداش‌های آستانه‌ها
        # روی هم جمع نمی‌شوند تا تعادل بازی حفظ شود.
        for threshold in (6, 4, 2):
            if count >= threshold:
                for stat, amount in tiers.get(threshold, {}).items():
                    bonuses[stat] += amount
                break

    # پاداش پت فعال بخشی از Stats مرکزی است؛ همهٔ مصرف‌کنندگان این سرویس
    # (پروفایل، مبارزه و دانجن) یک نتیجه می‌گیرند.
    async with AsyncSessionLocal() as session:
        active_pet = await session.execute(
            select(Pet)
            .join(CharacterPet, CharacterPet.pet_id == Pet.id)
            .where(
                CharacterPet.character_id == character.id,
                CharacterPet.active.is_(True),
            )
            .limit(1)
        )
        pet = active_pet.scalar_one_or_none()
        if pet is not None:
            pet_level = await session.scalar(
                select(CharacterPet.level).where(
                    CharacterPet.character_id == character.id,
                    CharacterPet.pet_id == pet.id,
                    CharacterPet.active.is_(True),
                ).limit(1)
            ) or 1
            pet_level = max(1, min(200, int(pet_level)))
            pet_multiplier = min(1.75, 1.0 + (pet_level - 1) * 0.03)
            rarity = str(getattr(pet, "rarity", "common") or "common").lower()
            # Pet power scales with the hero's level-based stats, so pets remain
            # useful in endgame without letting their old tiny seed values matter.
            pet_share = {
                "common": 0.02,
                "uncommon": 0.03,
                "rare": 0.04,
                "epic": 0.06,
                "legendary": 0.08,
                "mythic": 0.10,
                "divine": 0.12,
            }.get(rarity, 0.02)
            bonuses["attack"] += max(
                int((pet.bonus_attack or 0) * pet_multiplier),
                int(base.attack * pet_share * pet_multiplier),
            )
            bonuses["defense"] += max(
                int((pet.bonus_defense or 0) * pet_multiplier),
                int(base.defense * pet_share * pet_multiplier),
            )
            bonuses["hp"] += max(
                int((pet.bonus_hp or 0) * pet_multiplier),
                int(base.max_hp * pet_share * pet_multiplier),
            )

    final_max_hp = max(
        1,
        base.max_hp + bonuses["hp"],
    )

    final_max_mana = max(
        1,
        base.max_mana + bonuses["mana"],
    )

    return CharacterCombatStats(
        hp=final_max_hp,
        max_hp=final_max_hp,
        mana=final_max_mana,
        max_mana=final_max_mana,
        attack=max(
            1,
            base.attack + bonuses["attack"],
        ),
        magic_power=max(
            0,
            base.magic_power + bonuses["magic_power"],
        ),
        defense=max(
            0,
            base.defense + bonuses["defense"],
        ),
        magic_defense=max(
            0,
            base.magic_defense + bonuses["magic_defense"],
        ),
        speed=max(
            0,
            base.speed + bonuses["speed"],
        ),
        accuracy=max(
            0,
            base.accuracy + bonuses["accuracy"],
        ),
        luck=base.luck,
        critical=max(
            0,
            base.critical + bonuses["critical"],
        ),
    )