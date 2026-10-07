from __future__ import annotations

from dataclasses import dataclass
import random


MIN_DAMAGE = 1

# ضریب پایه کاهش Damage توسط Defense
DEFENSE_CONSTANT = 100.0

# تغییرات طبیعی Damage
RANDOM_MIN = 0.90
RANDOM_MAX = 1.10


ELEMENTAL_MULTIPLIERS: dict[str, dict[str, float]] = {
    "fire": {
        "fire": 0.75,
        "ice": 1.50,
        "water": 0.70,
    },
    "ice": {
        "ice": 0.75,
        "fire": 1.50,
        "water": 0.80,
    },
    "water": {
        "water": 0.75,
        "fire": 1.50,
        "electro": 0.80,
    },
    "electro": {
        "electro": 0.75,
        "water": 1.50,
        "earth": 0.70,
    },
    "earth": {
        "earth": 0.75,
        "electro": 1.50,
        "wind": 0.80,
    },
    "wind": {
        "wind": 0.75,
        "earth": 1.50,
        "ice": 0.80,
    },
    "shadow": {
        "shadow": 0.75,
        "light": 1.50,
    },
    "light": {
        "light": 0.75,
        "shadow": 1.50,
    },
    "blood": {
        "blood": 0.75,
        "shadow": 1.25,
    },
    "steel": {
        "steel": 0.75,
        "earth": 1.25,
        "fire": 0.80,
    },
}


@dataclass(frozen=True)
class DamageResult:
    damage: int
    base_damage: float
    defense_multiplier: float
    element_multiplier: float
    resistance_multiplier: float
    critical: bool
    random_multiplier: float


def get_element_multiplier(
    attack_element: str,
    defender_element: str,
) -> float:
    attack_element = attack_element.lower()
    defender_element = defender_element.lower()

    if attack_element == "neutral":
        return 1.0

    return ELEMENTAL_MULTIPLIERS.get(
        attack_element,
        {},
    ).get(
        defender_element,
        1.0,
    )


def get_resistance_multiplier(
    resistance: float,
) -> float:
    """
    Resistance به صورت اعشاری ذخیره می‌شود.

    مثال:
        0.20  -> 20% مقاومت -> 0.80 Damage
        0.50  -> 50% مقاومت -> 0.50 Damage
       -0.25  -> 25% ضعف      -> 1.25 Damage
    """

    resistance = max(-0.90, min(resistance, 0.90))

    return max(
        0.10,
        1.0 - resistance,
    )


def calculate_defense_multiplier(
    defense: int,
) -> float:
    """
    Defense به صورت نسبی Damage را کاهش می‌دهد.

    فرمول:

        100 / (100 + Defense)

    بنابراین Defense هیچ‌وقت Damage را کاملاً صفر نمی‌کند.
    """

    defense = max(0, defense)

    return DEFENSE_CONSTANT / (
        DEFENSE_CONSTANT + defense
    )


def calculate_damage(
    attack: int,
    defense: int,
    skill_power: float = 1.0,
    attack_element: str = "neutral",
    defender_element: str = "neutral",
    resistance: float = 0.0,
    critical: bool = False,
    critical_multiplier: float = 1.75,
    randomize: bool = True,
) -> DamageResult:

    attack = max(1, attack)
    defense = max(0, defense)
    skill_power = max(0.1, skill_power)

    base_damage = attack * skill_power

    defense_multiplier = calculate_defense_multiplier(
        defense
    )

    element_multiplier = get_element_multiplier(
        attack_element,
        defender_element,
    )

    resistance_multiplier = get_resistance_multiplier(
        resistance
    )

    if randomize:
        random_multiplier = random.uniform(
            RANDOM_MIN,
            RANDOM_MAX,
        )
    else:
        random_multiplier = 1.0

    critical_multiplier_value = (
        critical_multiplier
        if critical
        else 1.0
    )

    final_damage = (
        base_damage
        * defense_multiplier
        * element_multiplier
        * resistance_multiplier
        * critical_multiplier_value
        * random_multiplier
    )

    final_damage = max(
        MIN_DAMAGE,
        int(round(final_damage)),
    )

    return DamageResult(
        damage=final_damage,
        base_damage=base_damage,
        defense_multiplier=defense_multiplier,
        element_multiplier=element_multiplier,
        resistance_multiplier=resistance_multiplier,
        critical=critical,
        random_multiplier=random_multiplier,
    )