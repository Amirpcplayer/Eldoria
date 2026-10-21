from __future__ import annotations

import asyncio
from collections import Counter

import pytest
import pytest_asyncio
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.monster import Monster
from services.combat_service import get_random_variant_monster


GOBLIN_VARIANTS = {
    "goblin",
    "fire_goblin",
    "ice_goblin",
    "goblin_archer",
    "goblin_warrior",
    "goblin_shaman",
    "goblin_elite",
    "goblin_king",
}

GOLEM_VARIANTS = {
    "stone_golem",
    "fire_golem",
}


async def get_monster_by_variant(
    variant: str,
) -> Monster | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Monster).where(
                Monster.variant == variant,
                Monster.is_active.is_(True),
            )
        )


async def check_family(
    family_name: str,
    base_variant: str,
    expected_variants: set[str],
    trials: int = 100,
) -> bool:
    base_monster = await get_monster_by_variant(
        base_variant
    )

    if base_monster is None:
        print(
            f"❌ Base monster not found: "
            f"{base_variant}"
        )
        return False

    print("-" * 100)
    print(
        f"🧬 Testing {family_name} Random Variants"
    )
    print(
        f"Base: {base_monster.name} "
        f"| variant={base_monster.variant} "
        f"| monster_id={base_monster.id}"
    )
    print("-" * 100)

    counter: Counter[str] = Counter()

    for _ in range(trials):
        selected = await get_random_variant_monster(
            base_monster
        )

        if selected is None:
            print("❌ Random Variant returned None")
            return False

        if selected.family != family_name:
            print(
                f"❌ Wrong family: "
                f"expected={family_name} "
                f"got={selected.family}"
            )
            return False

        if selected.variant not in expected_variants:
            print(
                f"❌ Invalid variant: "
                f"{selected.variant}"
            )
            return False

        counter[selected.variant] += 1

    print()
    print(f"🎲 Total trials: {trials}")
    print()

    for variant in sorted(expected_variants):
        count = counter.get(variant, 0)
        percentage = (count / trials) * 100

        monster = await get_monster_by_variant(
            variant
        )

        monster_id = monster.id if monster else "N/A"

        print(
            f"{variant:<20} "
            f"ID={str(monster_id):<3} "
            f"{count:>3}/{trials} "
            f"({percentage:>5.1f}%)"
        )

    print()

    invalid = set(counter.keys()) - expected_variants

    if invalid:
        print(
            f"❌ Invalid variants detected: "
            f"{sorted(invalid)}"
        )
        return False

    if not counter:
        print("❌ No variants were selected.")
        return False

    print(
        f"✅ {family_name} Random Variant selection passed."
    )

    return True


@pytest.mark.asyncio
async def test_goblin_random_variants():
    result = await check_family(
        family_name="goblin",
        base_variant="goblin",
        expected_variants=GOBLIN_VARIANTS,
        trials=100,
    )

    assert result is True


@pytest.mark.asyncio
async def test_golem_random_variants():
    result = await check_family(
        family_name="golem",
        base_variant="stone_golem",
        expected_variants=GOLEM_VARIANTS,
        trials=100,
    )

    assert result is True


async def main() -> None:
    print("=" * 100)
    print(
        "WORLD ELDORIA - GOBLIN + GOLEM "
        "RANDOM VARIANT TEST"
    )
    print("=" * 100)
    print()

    goblin_ok = await check_family(
        family_name="goblin",
        base_variant="goblin",
        expected_variants=GOBLIN_VARIANTS,
        trials=100,
    )

    print()

    golem_ok = await check_family(
        family_name="golem",
        base_variant="stone_golem",
        expected_variants=GOLEM_VARIANTS,
        trials=100,
    )

    print()
    print("=" * 100)

    if goblin_ok and golem_ok:
        print("🎉 ALL RANDOM VARIANT TESTS PASSED")
        print()
        print("✅ Goblin Random Variant: PASS")
        print("✅ Golem Random Variant: PASS")
        print("✅ Family validation: PASS")
        print("✅ Variant validation: PASS")
    else:
        print("❌ RANDOM VARIANT TEST FAILED")

    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())