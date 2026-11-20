import asyncio
import sys
from pathlib import Path

# ------------------------------------------------------------------
# PROJECT ROOT
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from models.adventure import AdventureEnemy
from models.skill import Skill

from services.combat_service import (
    create_battle,
    get_battle,
    get_character_skills,
    player_skill,
    finish_battle,
    has_active_battle,
    redis,
)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
async def get_test_character() -> Character | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character)
            .order_by(Character.id)
            .limit(1)
        )


async def get_test_enemy() -> AdventureEnemy | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(AdventureEnemy)
            .where(AdventureEnemy.is_active.is_(True))
            .order_by(AdventureEnemy.id)
            .limit(1)
        )


async def get_skill(skill_id: int) -> Skill | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Skill).where(
                Skill.id == skill_id
            )
        )


async def cleanup_character_battles(telegram_id: int) -> None:
    keys = await redis.keys("eldoria:battle:*")

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


async def create_test_battle(
    telegram_id: int,
    enemy_id: int,
) -> dict | None:
    success, message, battle = await create_battle(
        telegram_id,
        enemy_id,
    )

    if not success or battle is None:
        print(f"❌ Battle creation failed: {message}")
        return None

    print(f"Battle ID={battle['battle_id']}")
    print(
        f"Enemy HP={battle['enemy_hp']}/{battle['enemy_max_hp']}"
    )
    print(
        f"Player Mana={battle['player_mana']}/{battle['player_max_mana']}"
    )

    return battle


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
async def main():
    print("=" * 80)
    print("WORLD ELDORIA - SKILL EDGE CASES TEST")
    print("=" * 80)

    character = await get_test_character()

    if character is None:
        print("❌ هیچ Character فعالی پیدا نشد.")
        return

    enemy = await get_test_enemy()

    if enemy is None:
        print("❌ هیچ Adventure Enemy فعالی پیدا نشد.")
        return

    character_skills = await get_character_skills(character.id)

    if not character_skills:
        print("❌ Character هیچ Skill فعالی ندارد.")
        return

    skill, character_skill = character_skills[0]

    print("\n👤 CHARACTER")
    print("-" * 80)
    print(f"ID={character.id}")
    print(f"Name={character.name}")
    print(f"Level={character.level}")
    print(f"Mana={character.mana}/{character.max_mana}")

    print("\n🔮 TEST SKILL")
    print("-" * 80)
    print(f"Skill ID={skill.id}")
    print(f"Name={skill.name}")
    print(f"Element={skill.element}")
    print(f"Skill Level={character_skill.level}")

    print("\n👹 TEST ENEMY")
    print("-" * 80)
    print(f"ID={enemy.id}")
    print(f"Name={enemy.name}")
    print(f"Level={enemy.level}")

    # ------------------------------------------------------------------
    # CLEAN OLD BATTLES
    # ------------------------------------------------------------------
    print("\n🧹 CLEANUP OLD BATTLES")
    print("-" * 80)

    await cleanup_character_battles(character.telegram_id)

    print("✅ Old battles cleaned.")

    all_passed = True

    # ------------------------------------------------------------------
    # TEST 1 - VALID SKILL
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("🧪 TEST 1 - VALID SKILL")
    print("=" * 80)

    battle = await create_test_battle(
        character.telegram_id,
        enemy.id,
    )

    if battle is None:
        return

    battle_id = battle["battle_id"]

    mana_before = battle["player_mana"]
    enemy_hp_before = battle["enemy_hp"]

    success, message, damage, victory, battle_after = await player_skill(
        battle_id,
        skill.id,
    )

    if not success:
        print(f"❌ Valid skill failed: {message}")
        all_passed = False
    elif damage <= 0:
        print("❌ Valid skill produced zero damage.")
        all_passed = False
    elif battle_after["player_mana"] >= mana_before:
        print("❌ Mana was not consumed.")
        all_passed = False
    elif battle_after["enemy_hp"] >= enemy_hp_before:
        print("❌ Enemy HP did not decrease.")
        all_passed = False
    else:
        print("✅ Valid skill executed correctly.")
        print(f"Message={message}")
        print(f"Damage={damage}")
        print(
            f"Mana: {mana_before} → "
            f"{battle_after['player_mana']}"
        )
        print(
            f"Enemy HP: {enemy_hp_before} → "
            f"{battle_after['enemy_hp']}"
        )

    await finish_battle(battle_id)

    # ------------------------------------------------------------------
    # TEST 2 - INSUFFICIENT MANA
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("🧪 TEST 2 - INSUFFICIENT MANA")
    print("=" * 80)

    battle = await create_test_battle(
        character.telegram_id,
        enemy.id,
    )

    if battle is None:
        return

    battle_id = battle["battle_id"]

    skill_mana_cost = (
        skill.mana_cost
        + (
            max(1, character_skill.level) - 1
        ) * {
            "fire": 8,
            "water": 8,
            "wind": 9,
            "earth": 10,
            "electro": 12,
            "ice": 13,
            "light": 18,
            "dark": 20,
        }.get(skill.element, 0)
    )

    battle["player_mana"] = max(
        0,
        skill_mana_cost - 1,
    )

    from services.combat_service import save_battle

    await save_battle(battle)

    success, message, damage, victory, battle_after = await player_skill(
        battle_id,
        skill.id,
    )

    if success:
        print("❌ Skill succeeded despite insufficient Mana.")
        all_passed = False
    else:
        print("✅ Insufficient Mana correctly blocked.")
        print(f"Message={message}")
        print(f"Damage={damage}")
        print(f"Victory={victory}")

    if battle_after is None:
        battle_after = await get_battle(battle_id)

    if battle_after is None:
        print("❌ Battle disappeared unexpectedly.")
        all_passed = False
    else:
        if battle_after["player_mana"] != battle["player_mana"]:
            print("❌ Mana changed despite failed Skill.")
            all_passed = False
        else:
            print("✅ Mana remained unchanged.")

    await finish_battle(battle_id)

    # ------------------------------------------------------------------
    # TEST 3 - INVALID SKILL ID
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("🧪 TEST 3 - INVALID SKILL ID")
    print("=" * 80)

    battle = await create_test_battle(
        character.telegram_id,
        enemy.id,
    )

    if battle is None:
        return

    battle_id = battle["battle_id"]

    enemy_hp_before = battle["enemy_hp"]
    mana_before = battle["player_mana"]

    invalid_skill_id = 999999

    success, message, damage, victory, battle_after = await player_skill(
        battle_id,
        invalid_skill_id,
    )

    if success:
        print("❌ Invalid Skill ID was accepted.")
        all_passed = False
    else:
        print("✅ Invalid Skill ID correctly rejected.")
        print(f"Message={message}")

    if battle_after is None:
        battle_after = await get_battle(battle_id)

    if battle_after is None:
        print("❌ Battle disappeared unexpectedly.")
        all_passed = False
    else:
        if battle_after["enemy_hp"] != enemy_hp_before:
            print("❌ Enemy HP changed after invalid Skill.")
            all_passed = False
        else:
            print("✅ Enemy HP remained unchanged.")

        if battle_after["player_mana"] != mana_before:
            print("❌ Mana changed after invalid Skill.")
            all_passed = False
        else:
            print("✅ Mana remained unchanged.")

    await finish_battle(battle_id)

    # ------------------------------------------------------------------
    # TEST 4 - SKILL NOT OWNED BY CHARACTER
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("🧪 TEST 4 - SKILL NOT OWNED BY CHARACTER")
    print("=" * 80)

    all_skills = []

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Skill)
            .order_by(Skill.id)
        )
        all_skills = list(result.scalars().all())

    owned_skill_ids = {
        owned_skill.id
        for owned_skill, _ in character_skills
    }

    foreign_skill = next(
        (
            item
            for item in all_skills
            if item.id not in owned_skill_ids
        ),
        None,
    )

    if foreign_skill is None:
        print(
            "⚠️ Skill دیگری برای تست مالکیت پیدا نشد."
        )
        print(
            "⚠️ این مورد Skip شد؛ خطای سیستم محسوب نمی‌شود."
        )
    else:
        battle = await create_test_battle(
            character.telegram_id,
            enemy.id,
        )

        if battle is None:
            return

        battle_id = battle["battle_id"]

        enemy_hp_before = battle["enemy_hp"]
        mana_before = battle["player_mana"]

        success, message, damage, victory, battle_after = await player_skill(
            battle_id,
            foreign_skill.id,
        )

        if success:
            print(
                "❌ Character توانست Skill متعلق به خودش نیست را اجرا کند."
            )
            all_passed = False
        else:
            print("✅ Skill غیرمالکانه correctly rejected.")
            print(f"Message={message}")

        if battle_after is None:
            battle_after = await get_battle(battle_id)

        if battle_after is None:
            print("❌ Battle disappeared unexpectedly.")
            all_passed = False
        else:
            if battle_after["enemy_hp"] != enemy_hp_before:
                print("❌ Enemy HP changed.")
                all_passed = False
            else:
                print("✅ Enemy HP unchanged.")

            if battle_after["player_mana"] != mana_before:
                print("❌ Mana changed.")
                all_passed = False
            else:
                print("✅ Mana unchanged.")

        await finish_battle(battle_id)

    # ------------------------------------------------------------------
    # FINAL CLEANUP
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("🧹 FINAL CLEANUP")
    print("=" * 80)

    await cleanup_character_battles(character.telegram_id)

    if await has_active_battle(character.telegram_id):
        print("❌ Active Battle still exists.")
        all_passed = False
    else:
        print("✅ No active Battle remains.")

    # ------------------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)

    if all_passed:
        print("✅ SKILL EDGE CASES TEST COMPLETED")
        print("✅ Valid Skill works.")
        print("✅ Insufficient Mana is blocked.")
        print("✅ Invalid Skill ID is rejected.")
        print("✅ Skill ownership is protected.")
        print("✅ Failed Skill attempts do not mutate Battle state.")
        print("✅ No active test Battle remains.")
        print("✅ No database values were intentionally modified.")
    else:
        print("❌ SKILL EDGE CASES TEST FAILED")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())