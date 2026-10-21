from __future__ import annotations

import asyncio
from collections import Counter

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.adventure import AdventureEnemy
from models.character import Character
from models.monster import Monster
from services.combat_service import (
    create_battle,
    finish_battle,
    get_battle,
)


TRIALS = 100

EXPECTED_VARIANTS = {
    "wolf": {
        "normal_wolf",
        "storm_wolf",
        "alpha_wolf",
        "fenrir",
    },
    "goblin": {
        "goblin",
        "fire_goblin",
        "ice_goblin",
        "goblin_archer",
        "goblin_warrior",
        "goblin_shaman",
        "goblin_elite",
        "goblin_king",
    },
    "golem": {
        "stone_golem",
        "fire_golem",
    },
}


async def get_test_character() -> Character | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Character)
            .order_by(Character.level.desc(), Character.id)
            .limit(1)
        )
        return result.scalar_one_or_none()


async def get_adventure_enemy_for_family(
    family: str,
) -> tuple[AdventureEnemy, Monster] | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AdventureEnemy, Monster)
            .join(
                Monster,
                AdventureEnemy.monster_id == Monster.id,
            )
            .where(
                AdventureEnemy.is_active.is_(True),
                Monster.is_active.is_(True),
                Monster.family == family,
            )
            .order_by(
                AdventureEnemy.id
            )
        )

        return result.first()


async def get_monster_by_id(
    monster_id: int,
) -> Monster | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Monster).where(
                Monster.id == monster_id,
                Monster.is_active.is_(True),
            )
        )


async def run_family_test(
    character: Character,
    family: str,
) -> str:
    result = await get_adventure_enemy_for_family(
        family
    )

    if result is None:
        print(
            f"❌ No active AdventureEnemy found "
            f"for family={family}"
        )
        return "FAIL"

    adventure_enemy, base_monster = result

    print("-" * 100)
    print(
        f"🧬 REAL ADVENTURE → COMBAT TEST: {family}"
    )
    print("-" * 100)

    print(
        f"👤 Character: {character.name} "
        f"| Level={character.level} "
        f"| Telegram ID={character.telegram_id}"
    )

    print(
        f"🗺️ AdventureEnemy: ID={adventure_enemy.id} "
        f"| level={adventure_enemy.level}"
    )

    print(
        f" Base Monster: {base_monster.name} "
        f"| ID={base_monster.id} "
        f"| family={base_monster.family} "
        f"| variant={base_monster.variant}"
    )

    print()

    # Adventure area access is enforced by create_battle().
    # If the player's level is too low, this family cannot
    # be tested through the real Adventure → Combat path yet.
    success, message, battle_data = await create_battle(
        telegram_id=character.telegram_id,
        enemy_id=adventure_enemy.id,
    )

    if not success:
        if "Level" in message or "Level" in str(message):
            print(
                "🔒 Adventure access blocked:"
            )
            print(
                f"   {message}"
            )
            print(
                "ℹ️ This is an expected Adventure "
                "unlock restriction, not a Random Variant failure."
            )
            return "BLOCKED"

        print(
            "❌ Initial battle creation failed:"
        )
        print(
            f"   {message}"
        )
        return "FAIL"

    if not battle_data:
        print(
            "❌ Battle data is empty."
        )
        return "FAIL"

    initial_battle_id = battle_data.get(
        "battle_id"
    )

    if initial_battle_id:
        try:
            await finish_battle(
                initial_battle_id
            )
        except Exception:
            pass

    counter: Counter[str] = Counter()

    for trial in range(1, TRIALS + 1):
        battle_data = None

        try:
            success, message, battle_data = await create_battle(
                telegram_id=character.telegram_id,
                enemy_id=adventure_enemy.id,
            )

            if not success:
                print(
                    f"❌ Trial {trial}: "
                    f"create_battle failed"
                )
                print(
                    f"   Message: {message}"
                )
                return "FAIL"

            if not battle_data:
                print(
                    f"❌ Trial {trial}: "
                    f"battle_data is empty"
                )
                return "FAIL"

            battle_id = battle_data.get(
                "battle_id"
            )

            if not battle_id:
                print(
                    f"❌ Trial {trial}: "
                    f"battle_id missing"
                )
                return "FAIL"

            stored_battle = await get_battle(
                battle_id
            )

            if stored_battle is None:
                print(
                    f"❌ Trial {trial}: "
                    f"battle could not be restored "
                    f"from Redis"
                )
                return "FAIL"

            variant = stored_battle.get(
                "enemy_variant"
            )

            monster_id = stored_battle.get(
                "monster_id"
            )

            if variant not in EXPECTED_VARIANTS[family]:
                print(
                    f"❌ Trial {trial}: "
                    f"invalid variant={variant!r}"
                )
                return "FAIL"

            if monster_id is None:
                print(
                    f"❌ Trial {trial}: "
                    f"monster_id missing"
                )
                return "FAIL"

            selected_monster = await get_monster_by_id(
                monster_id
            )

            if selected_monster is None:
                print(
                    f"❌ Trial {trial}: "
                    f"monster_id={monster_id} "
                    f"not found"
                )
                return "FAIL"

            if selected_monster.family != family:
                print(
                    f"❌ Trial {trial}: "
                    f"wrong family "
                    f"expected={family} "
                    f"got={selected_monster.family}"
                )
                return "FAIL"

            if selected_monster.variant != variant:
                print(
                    f"❌ Trial {trial}: "
                    f"Redis variant={variant} "
                    f"but DB variant="
                    f"{selected_monster.variant}"
                )
                return "FAIL"

            counter[variant] += 1

        except Exception as exc:
            print(
                f"❌ Trial {trial} crashed:"
            )
            print(
                f"   {type(exc).__name__}: {exc}"
            )
            return "FAIL"

        finally:
            if battle_data:
                battle_id = battle_data.get(
                    "battle_id"
                )

                if battle_id:
                    try:
                        await finish_battle(
                            battle_id
                        )
                    except Exception as exc:
                        print(
                            f"⚠️ Cleanup warning "
                            f"for {battle_id}: {exc}"
                        )

    print(
        f"🎲 Total real Adventure battles: "
        f"{TRIALS}"
    )
    print()

    for variant in sorted(
        EXPECTED_VARIANTS[family]
    ):
        count = counter.get(
            variant,
            0,
        )

        percentage = (
            count / TRIALS
        ) * 100

        async with AsyncSessionLocal() as session:
            monster = await session.scalar(
                select(Monster).where(
                    Monster.variant == variant,
                    Monster.is_active.is_(True),
                )
            )

        monster_id = (
            monster.id
            if monster
            else "N/A"
        )

        print(
            f"{variant:<20} "
            f"ID={str(monster_id):<3} "
            f"{count:>3}/{TRIALS} "
            f"({percentage:>5.1f}%)"
        )

    print()

    if not counter:
        print(
            f"❌ No {family} variants "
            f"were generated."
        )
        return "FAIL"

    print(
        f"✅ Real Adventure → Combat "
        f"test passed: {family}"
    )

    return "PASS"


async def verify_fresh_battle(
    character: Character,
) -> bool:
    result = await get_adventure_enemy_for_family(
        "wolf"
    )

    if result is None:
        print(
            "❌ Wolf AdventureEnemy not found."
        )
        return False

    adventure_enemy, _ = result

    battle_data = None

    try:
        success, message, battle_data = await create_battle(
            telegram_id=character.telegram_id,
            enemy_id=adventure_enemy.id,
        )

        if not success:
            print(
                "❌ Fresh battle creation failed."
            )
            print(
                f"   Message: {message}"
            )
            return False

        if not battle_data:
            print(
                "❌ Fresh battle_data is empty."
            )
            return False

        battle_id = battle_data.get(
            "battle_id"
        )

        if not battle_id:
            print(
                "❌ Fresh battle_id missing."
            )
            return False

        stored = await get_battle(
            battle_id
        )

        if stored is None:
            print(
                "❌ Fresh battle could not "
                "be restored from Redis."
            )
            return False

        print(
            "✅ Fresh battle creation "
            "and Redis restore passed."
        )

        return True

    finally:
        if battle_data:
            battle_id = battle_data.get(
                "battle_id"
            )

            if battle_id:
                try:
                    await finish_battle(
                        battle_id
                    )
                except Exception as exc:
                    print(
                        f"⚠️ Final cleanup warning: "
                        f"{exc}"
                    )


async def main() -> None:
    print("=" * 100)
    print(
        "WORLD ELDORIA - REAL ADVENTURE → COMBAT RANDOM VARIANT TEST"
    )
    print("=" * 100)
    print()

    character = await get_test_character()

    if character is None:
        print(
            "❌ No Character found in database."
        )
        return

    print(
        f"👤 Test Character: "
        f"{character.name} "
        f"| Level={character.level}"
    )
    print()

    results: dict[str, str] = {}

    for family in (
        "wolf",
        "goblin",
        "golem",
    ):
        results[family] = await run_family_test(
            character=character,
            family=family,
        )

        print()

    fresh_battle_ok = await verify_fresh_battle(
        character
    )

    print()
    print("=" * 100)

    hard_fail = any(
        result == "FAIL"
        for result in results.values()
    )

    if not hard_fail and fresh_battle_ok:
        print(
            "🎉 REAL ADVENTURE → COMBAT "
            "RANDOM VARIANT TEST PASSED"
        )
        print()

        for family, result in results.items():
            if result == "PASS":
                print(
                    f"✅ {family.capitalize()} "
                    f"Adventure → Combat"
                )
            elif result == "BLOCKED":
                print(
                    f"🔒 {family.capitalize()} "
                    f"Adventure → Combat "
                    f"(Level locked)"
                )

        print(
            "✅ Redis battle data"
        )
        print(
            "✅ Monster ID / Variant consistency"
        )
        print(
            "✅ Family validation"
        )
        print(
            "✅ Battle cleanup"
        )
        print(
            "✅ Fresh battle check"
        )
    else:
        print(
            "❌ REAL ADVENTURE → COMBAT "
            "TEST FAILED"
        )
        print()

        for family, result in results.items():
            print(
                f"{family.capitalize():<10} "
                f"{result}"
            )

        print(
            f"{'Fresh battle':<15} "
            f"{'PASS' if fresh_battle_ok else 'FAIL'}"
        )

    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())