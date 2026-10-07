from __future__ import annotations

from models.monster import Monster

from services.power_service import (
    MonsterStats,
    scale_monster_stats,
)


def calculate_monster_stats(
    monster: Monster,
    level: int,
) -> MonsterStats:
    """
    محاسبه Stats نهایی Monster بر اساس:

    - Stats پایه Monster
    - Level
    - power_multiplier مربوط به Variant

    این تابع هیچ تغییری در دیتابیس ایجاد نمی‌کند.
    """

    return scale_monster_stats(
        base_hp=monster.base_hp,
        base_attack=monster.base_attack,
        base_magic_power=monster.base_magic_power,
        base_defense=monster.base_defense,
        base_magic_defense=monster.base_magic_defense,
        base_speed=monster.base_speed,
        base_accuracy=monster.base_accuracy,
        base_luck=monster.base_luck,
        base_critical=monster.base_critical,
        level=level,
        power_multiplier=monster.power_multiplier,
    )