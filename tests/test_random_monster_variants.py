from __future__ import annotations

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.redis import redis

from models.adventure import AdventureEnemy
from models.character import Character

from services.combat_service import (
    create_battle,
    finish_battle,
    get_battle,
)


TRIALS = 100


async def get_test_character() -> Character | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character)
            .order_by(Character.id)
            .limit(1)
        )


async def get_wolf_enemy() -> AdventureEnemy | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(AdventureEnemy)
            .where(
                AdventureEnemy.monster_id == 1,
                AdventureEnemy.is_active.is_(True),
            )
            .order_by(AdventureEnemy.id)
            .limit(1)
        )


async def cleanup_character_battles(
    telegram_id: int,
) -> int:

    deleted = 0

    async for key in redis.scan_iter(
        match="eldoria:battle:*"
    ):

        if isinstance(key, bytes):
            key = key.decode("utf-8")

        if key.startswith(
            "eldoria:battle_reward:"
        ):
            continue

        data = await redis.hgetall(key)

        if not data:
            continue

        stored_telegram_id = data.get(
            "telegram_id"
        )

        if isinstance(
            stored_telegram_id,
            bytes,
        ):
            stored_telegram_id = (
                stored_telegram_id.decode(
                    "utf-8"
                )
            )

        if stored_telegram_id is None:
            continue

        if int(stored_telegram_id) != telegram_id:
            continue

        await redis.delete(key)

        deleted += 1

    return deleted


async def main():

    print("=" * 100)
    print(
        "WORLD ELDORIA - RANDOM MONSTER VARIANT TEST"
    )
    print("=" * 100)

    character = await get_test_character()

    if character is None:
        print("❌ No character found.")
        return

    enemy = await get_wolf_enemy()

    if enemy is None:
        print(
            "❌ Wolf AdventureEnemy not found."
        )
        return

    print(
        f"👤 Character: {character.name} "
        f"| Level={character.level} "
        f"| Character ID={character.id}"
    )

    print(
        f"🐺 Base Enemy: {enemy.name} "
        f"| Enemy ID={enemy.id} "
        f"| Monster ID={enemy.monster_id}"
    )

    print("-" * 100)

    old_battles = await cleanup_character_battles(
        character.telegram_id
    )

    if old_battles:
        print(
            f"🧹 Removed {old_battles} stale battle(s)."
        )

    print(
        f"Running {TRIALS} battles..."
    )
    print()

    variants: dict[str, int] = {}
    monster_ids: dict[int, int] = {}

    successful_trials = 0

    for index in range(
        1,
        TRIALS + 1,
    ):

        battle_id = None

        try:

            success, message, battle = (
                await create_battle(
                    character.telegram_id,
                    enemy.id,
                )
            )

            if not success or battle is None:
                print(
                    f"❌ Trial {index}: "
                    f"{message}"
                )

                await cleanup_character_battles(
                    character.telegram_id
                )

                continue

            battle_id = battle[
                "battle_id"
            ]

            restored = await get_battle(
                battle_id
            )

            if restored is None:
                print(
                    f"❌ Trial {index}: "
                    "Battle could not be restored from Redis."
                )
                continue

            variant = restored.get(
                "enemy_variant",
                "unknown",
            )

            monster_id = restored.get(
                "monster_id",
                0,
            )

            variants[variant] = (
                variants.get(
                    variant,
                    0,
                )
                + 1
            )

            monster_ids[monster_id] = (
                monster_ids.get(
                    monster_id,
                    0,
                )
                + 1
            )

            successful_trials += 1

            print(
                f"#{index:03d} "
                f"Variant={variant:<15} "
                f"MonsterID={monster_id:<3} "
                f"Level={restored['enemy_level']:<2} "
                f"HP={restored['enemy_max_hp']:<4} "
                f"ATK={restored['enemy_attack']:<3} "
                f"DEF={restored['enemy_defense']:<3} "
                f"MDEF={restored['enemy_magic_defense']:<3} "
                f"Element={restored.get('enemy_element', 'neutral')}"
            )

        except Exception as exc:

            print(
                f"❌ Trial {index} crashed: "
                f"{type(exc).__name__}: {exc}"
            )

        finally:

            if battle_id:
                await finish_battle(
                    battle_id
                )

            await cleanup_character_battles(
                character.telegram_id
            )

    print()
    print("=" * 100)
    print("RESULT")
    print("=" * 100)

    print(
        f"\n✅ Successful battles: "
        f"{successful_trials}/{TRIALS}"
    )

    print("\n🧬 VARIANTS:")

    if not variants:
        print(
            "  ❌ No variants were generated."
        )

    for variant, count in sorted(
        variants.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        percentage = (
            count / successful_trials * 100
            if successful_trials
            else 0
        )

        print(
            f"  {variant:<15} "
            f"{count:>3} "
            f"({percentage:>5.1f}%)"
        )

    print("\n MONSTER IDS:")

    if not monster_ids:
        print(
            "  ❌ No Monster IDs recorded."
        )

    for monster_id, count in sorted(
        monster_ids.items()
    ):
        print(
            f"  Monster ID {monster_id:<3} "
            f"=> {count} battle(s)"
        )

    expected_variants = {
        "normal_wolf",
        "storm_wolf",
        "alpha_wolf",
        "fenrir",
    }

    found_variants = set(
        variants.keys()
    )

    unexpected = (
        found_variants
        - expected_variants
    )

    print()

    if unexpected:
        print(
            "❌ Unexpected variants found:"
        )
        for variant in sorted(
            unexpected
        ):
            print(
                f"   - {variant}"
            )

    if successful_trials == 0:
        print(
            "❌ No battles were successfully created."
        )

    elif unexpected:
        print(
            "❌ Random Variant test failed."
        )

    elif len(found_variants) >= 2:
        print(
            "✅ Random Variant is working."
        )

    elif len(found_variants) == 1:
        print(
            "⚠️ Only one variant appeared."
        )
        print(
            "This can happen with random selection, "
            "but run the test again if needed."
        )

    print()

    remaining = await cleanup_character_battles(
        character.telegram_id
    )

    if remaining:
        print(
            f"🧹 Final cleanup: "
            f"{remaining} battle(s) removed."
        )
    else:
        print(
            "🧹 Final cleanup: OK"
        )

    print()
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())