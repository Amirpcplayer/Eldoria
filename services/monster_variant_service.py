from __future__ import annotations

import random
from dataclasses import dataclass

from sqlalchemy import select

from database.database import AsyncSessionLocal

from models.monster import Monster


@dataclass(frozen=True)
class MonsterVariantChoice:
    """
    تعریف خانواده و Variantهای قابل انتخاب تصادفی.

    weight:
        احتمال نسبی انتخاب Variant.
    """

    variant: str
    weight: int


# ============================================================
# MONSTER FAMILIES
# ============================================================

MONSTER_FAMILIES: dict[str, tuple[MonsterVariantChoice, ...]] = {
    "wolf": (
        MonsterVariantChoice(
            variant="normal_wolf",
            weight=60,
        ),
        MonsterVariantChoice(
            variant="storm_wolf",
            weight=25,
        ),
        MonsterVariantChoice(
            variant="alpha_wolf",
            weight=12,
        ),
        MonsterVariantChoice(
            variant="fenrir",
            weight=3,
        ),
    ),
}


# ============================================================
# FAMILY DETECTION
# ============================================================

VARIANT_FAMILY_MAP: dict[str, str] = {
    # Wolves
    "normal_wolf": "wolf",
    "storm_wolf": "wolf",
    "alpha_wolf": "wolf",
    "fenrir": "wolf",
}


def get_monster_family(
    monster: Monster,
) -> str | None:
    """
    خانواده Monster را از روی Variant مشخص می‌کند.
    """

    variant = getattr(
        monster,
        "variant",
        None,
    )

    if not variant:
        return None

    return VARIANT_FAMILY_MAP.get(
        variant
    )


def get_family_variants(
    family: str,
) -> tuple[MonsterVariantChoice, ...]:
    """
    تمام Variantهای یک خانواده را برمی‌گرداند.
    """

    return MONSTER_FAMILIES.get(
        family,
        (),
    )


# ============================================================
# RANDOM VARIANT
# ============================================================

def choose_random_variant(
    family: str,
) -> str | None:
    """
    یک Variant تصادفی از خانواده انتخاب می‌کند.

    احتمال‌ها برای Wolf:

    normal_wolf = 60%
    storm_wolf  = 25%
    alpha_wolf  = 12%
    fenrir      = 3%
    """

    variants = get_family_variants(
        family
    )

    if not variants:
        return None

    choices = [
        item.variant
        for item in variants
    ]

    weights = [
        item.weight
        for item in variants
    ]

    return random.choices(
        choices,
        weights=weights,
        k=1,
    )[0]


# ============================================================
# RANDOM VARIANT MONSTER
# ============================================================

async def get_random_variant_monster(
    base_monster: Monster,
) -> Monster:
    """
    از روی Monster پایه، یک Variant تصادفی
    از همان خانواده انتخاب می‌کند.

    اگر خانواده‌ای برای Monster تعریف نشده باشد،
    همان Monster پایه برگردانده می‌شود.
    """

    family = get_monster_family(
        base_monster
    )

    if family is None:
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
                Monster.is_active.is_(True),
            )
        )

        if monster is None:
            return base_monster

        return monster


# ============================================================
# FAMILY BY VARIANT
# ============================================================

async def get_random_family_variant(
    family: str,
) -> Monster | None:
    """
    مستقیماً از روی نام خانواده،
    یک Monster Variant تصادفی برمی‌گرداند.
    """

    variant = choose_random_variant(
        family
    )

    if variant is None:
        return None

    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Monster).where(
                Monster.variant == variant,
                Monster.is_active.is_(True),
            )
        )


# ============================================================
# DEBUG / TEST HELPERS
# ============================================================

def get_variant_distribution(
    family: str,
) -> dict[str, int]:
    """
    وزن‌های انتخاب Variant را برای تست برمی‌گرداند.
    """

    variants = get_family_variants(
        family
    )

    return {
        item.variant: item.weight
        for item in variants
    }