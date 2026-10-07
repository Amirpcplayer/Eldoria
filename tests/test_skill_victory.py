import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.adventure import AdventureEnemy
from models.character_skill import CharacterSkill
from models.skill import Skill

from services.combat_service import (
    create_battle,
    get_battle,
    player_skill,
    finish_victory,
    finish_battle,
    save_battle,
    has_active_battle,
    redis,
)


async def cleanup_existing_battle(telegram_id: int) -> None:
    """
    Battleهای قبلی همین بازیکن را از Redis پاک می‌کند
    تا تست از وضعیت تمیز شروع شود.
    """

    if not await has_active_battle(telegram_id):
        return

    print()
    print("🧹 ACTIVE BATTLE CLEANUP")
    print("-" * 80)
    print("⚠️ یک Battle قبلی پیدا شد.")
    print("🧹 در حال پاک‌سازی Battle قبلی...")

    keys = await redis.keys("eldoria:battle:*")

    removed = False

    for key in keys:
        if isinstance(key, bytes):
            key = key.decode()

        battle_id = key.split(":")[-1]

        battle = await get_battle(battle_id)

        if battle is None:
            continue

        if battle.get("telegram_id") != telegram_id:
            continue

        await finish_battle(battle_id)

        print(f"✅ Battle {battle_id} removed.")

        removed = True

    if not removed:
        print(
            "⚠️ Battle فعال پیدا شد اما کلید آن پیدا نشد."
        )


async def main() -> None:
    print("=" * 80)
    print("WORLD ELDORIA - SKILL VICTORY TEST")
    print("=" * 80)

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character)
            .order_by(Character.id)
        )

        enemy = await session.scalar(
            select(AdventureEnemy)
            .where(
                AdventureEnemy.is_active.is_(True)
            )
            .order_by(AdventureEnemy.id)
        )

        if character is None:
            print("❌ هیچ Characterای پیدا نشد.")
            return

        if enemy is None:
            print("❌ هیچ AdventureEnemyای پیدا نشد.")
            return

        result = await session.execute(
            select(
                Skill,
                CharacterSkill,
            )
            .join(
                CharacterSkill,
                CharacterSkill.skill_id == Skill.id,
            )
            .where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.unlocked.is_(True),
                Skill.is_active.is_(True),
            )
            .order_by(
                CharacterSkill.slot,
                Skill.id,
            )
        )

        skills = list(result.all())

    if not skills:
        print(
            "❌ هیچ Skill فعال و Unlock شده‌ای پیدا نشد."
        )
        return

    skill, character_skill = skills[0]

    print()
    print("👤 PLAYER")
    print("-" * 80)
    print(f"Name={character.name}")
    print(f"Level={character.level}")
    print(f"XP={character.xp}")
    print(f"Skill XP={character.skill_xp}")
    print(f"Gold={character.gold}")

    print()
    print("🔮 SKILL")
    print("-" * 80)
    print(f"Name={skill.name}")
    print(f"Skill ID={skill.id}")
    print(f"Skill Level={character_skill.level}")
    print(f"Element={skill.element}")

    print()
    print("👹 ENEMY")
    print("-" * 80)
    print(f"Name={enemy.name}")
    print(f"Enemy ID={enemy.id}")

    # ---------------------------------------------------------------
    # CLEANUP OLD BATTLE
    # ---------------------------------------------------------------

    await cleanup_existing_battle(
        character.telegram_id
    )

    print()
    print("=" * 80)
    print("⚔️ CREATE BATTLE")
    print("=" * 80)

    success, message, battle = await create_battle(
        character.telegram_id,
        enemy.id,
    )

    print(f"Success={success}")
    print(f"Message={message}")

    if not success or battle is None:
        return

    battle_id = battle["battle_id"]

    print(f"Battle ID={battle_id}")
    print(
        f"Enemy HP="
        f"{battle['enemy_hp']}/"
        f"{battle['enemy_max_hp']}"
    )
    print(
        f"Player Mana="
        f"{battle['player_mana']}/"
        f"{battle['player_max_mana']}"
    )

    # ---------------------------------------------------------------
    # TEST ONLY
    # دشمن را فقط در Battle Redis روی 1 HP قرار می‌دهیم.
    # AdventureEnemy دیتابیس اصلاً تغییر نمی‌کند.
    # ---------------------------------------------------------------

    battle["enemy_hp"] = 1

    await save_battle(battle)

    battle = await get_battle(
        battle_id
    )

    if battle is None:
        print(
            "❌ Battle بعد از تنظیم HP پیدا نشد."
        )
        return

    print()
    print("🧪 TEST SETUP")
    print("-" * 80)
    print(
        f"Enemy HP forced to="
        f"{battle['enemy_hp']}"
    )

    # ---------------------------------------------------------------
    # PLAYER USES SKILL
    # ---------------------------------------------------------------

    print()
    print("=" * 80)
    print("🔮 PLAYER USES SKILL")
    print("=" * 80)

    old_xp = character.xp
    old_skill_xp = character.skill_xp
    old_gold = character.gold

    success, skill_message, damage, victory, battle = await player_skill(
        battle_id,
        skill.id,
    )

    print(f"Success={success}")
    print(f"Message={skill_message}")
    print(f"Damage={damage}")
    print(f"Victory={victory}")

    if not success or battle is None:
        print(
            "❌ Skill execution failed."
        )
        await finish_battle(
            battle_id
        )
        return

    print()
    print(
        f"Enemy HP after skill="
        f"{battle['enemy_hp']}"
    )

    if not victory:
        print(
            "❌ Skill should have defeated "
            "the enemy."
        )
        await finish_battle(
            battle_id
        )
        return

    print(
        "✅ Skill defeated the enemy."
    )

    # ---------------------------------------------------------------
    # FINISH VICTORY
    # ---------------------------------------------------------------

    print()
    print("=" * 80)
    print("🏆 FINISH VICTORY")
    print("=" * 80)

    reward_result = await finish_victory(
        battle_id
    )

    print(
        f"Reward Result={reward_result}"
    )

    if not reward_result[0]:
        print(
            "❌ Victory reward failed."
        )
        return

    (
        _,
        xp_reward,
        skill_xp_reward,
        gold_reward,
        levels_gained,
    ) = reward_result

    print()
    print(
        f"✨ XP Reward={xp_reward}"
    )
    print(
        f"🔮 Skill XP Reward={skill_xp_reward}"
    )
    print(
        f"💰 Gold Reward={gold_reward}"
    )
    print(
        f"🎉 Levels Gained={levels_gained}"
    )

    # ---------------------------------------------------------------
    # DATABASE VERIFICATION
    # ---------------------------------------------------------------

    print()
    print("=" * 80)
    print("🔄 DATABASE VERIFICATION")
    print("=" * 80)

    async with AsyncSessionLocal() as session:

        updated_character = await session.scalar(
            select(Character).where(
                Character.id == character.id
            )
        )

        if updated_character is None:
            print(
                "❌ Character بعد از Reward پیدا نشد."
            )
            return

        print(
            f"Old XP={old_xp}"
        )
        print(
            f"New XP={updated_character.xp}"
        )

        print(
            f"Old Skill XP={old_skill_xp}"
        )
        print(
            f"New Skill XP={updated_character.skill_xp}"
        )

        print(
            f"Old Gold={old_gold}"
        )
        print(
            f"New Gold={updated_character.gold}"
        )

        print(
            f"Current Level="
            f"{updated_character.level}"
        )

        expected_skill_xp = (
            old_skill_xp +
            skill_xp_reward
        )

        expected_gold = (
            old_gold +
            gold_reward
        )

        if updated_character.skill_xp != expected_skill_xp:
            print(
                "❌ Skill XP reward "
                "calculation mismatch."
            )
            return

        if updated_character.gold != expected_gold:
            print(
                "❌ Gold reward "
                "calculation mismatch."
            )
            return

        print()
        print(
            "✅ Skill XP reward "
            "applied correctly."
        )

        print(
            "✅ Gold reward "
            "applied correctly."
        )

    # ---------------------------------------------------------------
    # REDIS VERIFICATION
    # ---------------------------------------------------------------

    print()
    print("=" * 80)
    print("🔄 REDIS CLEANUP VERIFICATION")
    print("=" * 80)

    remaining_battle = await get_battle(
        battle_id
    )

    if remaining_battle is None:
        print(
            "✅ Battle removed from Redis "
            "after victory."
        )
    else:
        print(
            "⚠️ Battle still exists in Redis."
        )

        await finish_battle(
            battle_id
        )

        print(
            "✅ Battle cleanup completed manually."
        )

    print()
    print("=" * 80)
    print("✅ SKILL VICTORY TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())