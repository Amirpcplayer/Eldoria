from __future__ import annotations


# ============================================================
# LEVEL SETTINGS
# ============================================================

MIN_MONSTER_LEVEL = 1
MAX_MONSTER_LEVEL = 100


# ============================================================
# MONSTER LEVEL CALCULATOR
# ============================================================

def calculate_monster_level(
    character_level: int,
    enemy_level: int,
    area_min_level: int,
    area_max_level: int,
) -> int:
    """
    تعیین Level نهایی هیولا برای مبارزه.

    enemy_level:
        Level پایه‌ای که برای آن هیولا در Adventure تعریف شده.

    character_level:
        Level فعلی قهرمان.

    area_min_level / area_max_level:
        محدوده Level منطقه.

    منطق:
        - Level پایه هیولا حفظ می‌شود.
        - اگر قهرمان خیلی بالاتر یا پایین‌تر باشد،
          Level دشمن بدون خروج از محدوده منطقه تنظیم می‌شود.
        - هیچ Levelی از 1 تا 100 خارج نمی‌شود.
    """

    character_level = max(
        MIN_MONSTER_LEVEL,
        min(character_level, MAX_MONSTER_LEVEL),
    )

    enemy_level = max(
        MIN_MONSTER_LEVEL,
        min(enemy_level, MAX_MONSTER_LEVEL),
    )

    area_min_level = max(
        MIN_MONSTER_LEVEL,
        min(area_min_level, MAX_MONSTER_LEVEL),
    )

    area_max_level = max(
        area_min_level,
        min(area_max_level, MAX_MONSTER_LEVEL),
    )

    # --------------------------------------------------------
    # پایه Level هیولا
    # --------------------------------------------------------

    final_level = enemy_level

    # --------------------------------------------------------
    # اگر هیولا خیلی پایین‌تر از قهرمان باشد
    # --------------------------------------------------------

    if character_level > enemy_level + 3:

        final_level = character_level - 3

    # --------------------------------------------------------
    # اگر هیولا خیلی بالاتر از قهرمان باشد
    # --------------------------------------------------------

    elif enemy_level > character_level + 3:

        final_level = character_level + 3

    # --------------------------------------------------------
    # محدود کردن به محدوده منطقه
    # --------------------------------------------------------

    final_level = max(
        area_min_level,
        final_level,
    )

    final_level = min(
        area_max_level,
        final_level,
    )

    # --------------------------------------------------------
    # محدودیت نهایی سیستم
    # --------------------------------------------------------

    final_level = max(
        MIN_MONSTER_LEVEL,
        min(final_level, MAX_MONSTER_LEVEL),
    )

    return final_level