from __future__ import annotations

from dataclasses import dataclass


# ============================================================
# LEVEL SETTINGS
# ============================================================

MAX_LEVEL = 100


# ============================================================
# POWER CURVE
# ============================================================

def get_level_multiplier(level: int) -> float:
    """
    ضریب رشد قدرت بر اساس Level.

    رشد به صورت خطی ساده نیست تا Levelهای بالاتر
    بیش از حد ضعیف یا بیش از حد قوی نشوند.
    """

    level = max(1, min(level, MAX_LEVEL))

    return 1.0 + ((level - 1) * 0.12)


# ============================================================
# HERO BASE STATS
# ============================================================

@dataclass(frozen=True)
class HeroBaseStats:
    hp: int
    mana: int
    attack: int
    magic_power: int
    defense: int
    magic_defense: int
    speed: int
    accuracy: int
    luck: int
    critical: int


def get_hero_base_stats(level: int) -> HeroBaseStats:
    """
    Stats پایه قهرمان بر اساس Level.

    این اعداد قبل از تجهیزات هستند.
    """

    level = max(1, min(level, MAX_LEVEL))

    multiplier = get_level_multiplier(level)

    return HeroBaseStats(
        hp=max(1, round(100 * multiplier)),
        mana=max(1, round(100 * multiplier)),
        attack=max(1, round(10 * multiplier)),
        magic_power=max(1, round(10 * multiplier)),
        defense=max(1, round(8 * multiplier)),
        magic_defense=max(1, round(8 * multiplier)),
        speed=max(1, round(10 * multiplier)),
        accuracy=max(1, round(10 * multiplier)),
        luck=max(1, round(5 * multiplier)),
        critical=max(1, round(5 * multiplier)),
    )


# ============================================================
# MONSTER STATS
# ============================================================

@dataclass(frozen=True)
class MonsterStats:
    hp: int
    attack: int
    magic_power: int
    defense: int
    magic_defense: int
    speed: int
    accuracy: int
    luck: int
    critical: int


def scale_monster_stats(
    base_hp: int,
    base_attack: int,
    base_magic_power: int,
    base_defense: int,
    base_magic_defense: int,
    base_speed: int,
    base_accuracy: int,
    base_luck: int,
    base_critical: int,
    level: int,
    power_multiplier: float = 1.0,
) -> MonsterStats:
    """
    تبدیل Stats پایه Monster به Stats نهایی بر اساس Level
    و ضریب Variant.
    """

    level = max(1, min(level, MAX_LEVEL))

    level_multiplier = get_level_multiplier(level)

    final_multiplier = (
        level_multiplier
        * max(power_multiplier, 0.1)
    )

    return MonsterStats(
        hp=max(
            1,
            round(base_hp * final_multiplier),
        ),
        attack=max(
            1,
            round(base_attack * final_multiplier),
        ),
        magic_power=max(
            1,
            round(base_magic_power * final_multiplier),
        ),
        defense=max(
            1,
            round(base_defense * final_multiplier),
        ),
        magic_defense=max(
            1,
            round(base_magic_defense * final_multiplier),
        ),
        speed=max(
            1,
            round(base_speed * final_multiplier),
        ),
        accuracy=max(
            1,
            round(base_accuracy * final_multiplier),
        ),
        luck=max(
            1,
            round(base_luck * final_multiplier),
        ),
        critical=max(
            1,
            round(base_critical * final_multiplier),
        ),
    )