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

    # Level 100 baseline is intentionally endgame-scale so an unequipped
    # hero can survive and contribute against a level-150 group boss.
    # Equipment is added separately by character_stats_service.
    growth = (level - 1) ** 2
    return HeroBaseStats(
        hp=max(100, 100 + 50 * growth),
        mana=max(100, 100 + 50 * growth),
        attack=max(10, 10 + int(5.1 * growth)),
        magic_power=max(10, 10 + int(5.1 * growth)),
        defense=max(8, 8 + int(2.55 * growth)),
        magic_defense=max(8, 8 + int(2.55 * growth)),
        speed=max(10, 10 + int(0.35 * growth)),
        accuracy=max(10, 10 + int(0.35 * growth)),
        luck=max(5, 5 + int(0.08 * growth)),
        critical=max(5, min(75, 5 + int(0.08 * growth))),
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