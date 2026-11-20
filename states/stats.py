RACE_BONUSES = {
    "human": {
        "hp": 100,
        "mana": 100,
        "attack": 10,
        "magic_power": 10,
        "defense": 10,
        "magic_defense": 10,
        "speed": 10,
        "accuracy": 10,
        "luck": 10,
        "critical": 5,
    },

    "elf": {
        "hp": 95,
        "mana": 110,
        "attack": 10,
        "magic_power": 12,
        "defense": 9,
        "magic_defense": 11,
        "speed": 11,
        "accuracy": 11,
        "luck": 10,
        "critical": 5,
    },

    "demon": {
        "hp": 100,
        "mana": 100,
        "attack": 11,
        "magic_power": 10,
        "defense": 10,
        "magic_defense": 9,
        "speed": 10,
        "accuracy": 10,
        "luck": 10,
        "critical": 6,
    },

    "dwarf": {
        "hp": 110,
        "mana": 95,
        "attack": 10,
        "magic_power": 9,
        "defense": 12,
        "magic_defense": 10,
        "speed": 9,
        "accuracy": 10,
        "luck": 10,
        "critical": 5,
    },

    "dragonite": {
        "hp": 108,
        "mana": 108,
        "attack": 11,
        "magic_power": 11,
        "defense": 11,
        "magic_defense": 11,
        "speed": 10,
        "accuracy": 10,
        "luck": 10,
        "critical": 5,
    },

    "fairy": {
        "hp": 92,
        "mana": 112,
        "attack": 8,
        "magic_power": 12,
        "defense": 9,
        "magic_defense": 11,
        "speed": 11,
        "accuracy": 11,
        "luck": 11,
        "critical": 5,
    },

    "vampire": {
        "hp": 100,
        "mana": 100,
        "attack": 11,
        "magic_power": 10,
        "defense": 10,
        "magic_defense": 10,
        "speed": 11,
        "accuracy": 10,
        "luck": 10,
        "critical": 6,
    },

    "werewolf": {
        "hp": 105,
        "mana": 95,
        "attack": 12,
        "magic_power": 8,
        "defense": 10,
        "magic_defense": 9,
        "speed": 12,
        "accuracy": 10,
        "luck": 10,
        "critical": 6,
    },
}


def get_base_stats(race: str) -> dict:
    """
    دریافت Stats پایه بر اساس نژاد.
    """

    stats = RACE_BONUSES.get(race)

    if stats is None:
        return RACE_BONUSES["human"].copy()

    return stats.copy()