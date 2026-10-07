from __future__ import annotations

from dataclasses import dataclass

from models.character import Character
from services.equipment_service import get_equipped_equipments
from services.power_service import get_hero_base_stats


# ============================================================
# FINAL CHARACTER STATS
# ============================================================

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


# ============================================================
# BASE STATS
# ============================================================

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


# ============================================================
# FINAL STATS WITH EQUIPMENT
# ============================================================

async def calculate_character_combat_stats(
    character: Character,
) -> CharacterCombatStats:

    base = calculate_character_base_stats(
        character,
    )

    equipped_items = await get_equipped_equipments(
        character.id,
    )

    attack_bonus = 0
    magic_power_bonus = 0
    defense_bonus = 0
    magic_defense_bonus = 0
    hp_bonus = 0
    mana_bonus = 0
    speed_bonus = 0
    accuracy_bonus = 0
    critical_bonus = 0

    for character_equipment, equipment in equipped_items:

        quantity = max(
            1,
            character_equipment.quantity,
        )

        attack_bonus += (
            equipment.attack * quantity
        )

        magic_power_bonus += (
            equipment.magic_power * quantity
        )

        defense_bonus += (
            equipment.defense * quantity
        )

        magic_defense_bonus += (
            equipment.magic_defense * quantity
        )

        hp_bonus += (
            equipment.hp * quantity
        )

        mana_bonus += (
            equipment.mana * quantity
        )

        speed_bonus += (
            equipment.speed * quantity
        )

        accuracy_bonus += (
            equipment.accuracy * quantity
        )

        critical_bonus += (
            equipment.critical * quantity
        )

    final_max_hp = max(
        1,
        base.max_hp + hp_bonus,
    )

    final_max_mana = max(
        1,
        base.max_mana + mana_bonus,
    )

    return CharacterCombatStats(
        hp=min(
            base.hp + hp_bonus,
            final_max_hp,
        ),

        max_hp=final_max_hp,

        mana=min(
            base.mana + mana_bonus,
            final_max_mana,
        ),

        max_mana=final_max_mana,

        attack=(
            base.attack
            + attack_bonus
        ),

        magic_power=(
            base.magic_power
            + magic_power_bonus
        ),

        defense=(
            base.defense
            + defense_bonus
        ),

        magic_defense=(
            base.magic_defense
            + magic_defense_bonus
        ),

        speed=(
            base.speed
            + speed_bonus
        ),

        accuracy=(
            base.accuracy
            + accuracy_bonus
        ),

        luck=base.luck,

        critical=(
            base.critical
            + critical_bonus
        ),
    )