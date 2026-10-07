import asyncio
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from sqlalchemy import select

from database.database import AsyncSessionLocal

from models.character import Character
from models.character_skill import CharacterSkill
from models.skill import Skill
from models.monster import Monster
from models.adventure import AdventureEnemy

from services.combat_service import (
    create_battle,
    get_battle,
    get_character_skill,
    player_skill,
    finish_battle,
    has_active_battle,
)

from services.skill_service import get_skill_mana_cost


# ============================================================
# TEST CONFIGURATION
# ============================================================

TEST_CHARACTER_ID = 1
TEST_SKILL_ID = 1
TEST_ENEMY_ID = 1


# ============================================================
# MAIN TEST
# ============================================================

async def main():

    print("=" * 80)
    print("WORLD ELDORIA - SKILL COMBAT INTEGRATION TEST")
    print("=" * 80)

    battle_id = None

    # ========================================================
    # LOAD TEST DATA
    # ========================================================

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == TEST_CHARACTER_ID
            )
        )

        skill = await session.scalar(
            select(Skill).where(
                Skill.id == TEST_SKILL_ID,
                Skill.is_active.is_(True),
            )
        )

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == TEST_CHARACTER_ID,
                CharacterSkill.skill_id == TEST_SKILL_ID,
            )
        )

        enemy = await session.scalar(
            select(AdventureEnemy).where(
                AdventureEnemy.id == TEST_ENEMY_ID,
                AdventureEnemy.is_active.is_(True),
            )
        )

        monster = None

        if enemy is not None and enemy.monster_id is not None:

            monster = await session.scalar(
                select(Monster).where(
                    Monster.id == enemy.monster_id,
                    Monster.is_active.is_(True),
                )
            )

        assert character is not None, "Character not found."
        assert skill is not None, "Skill not found."
        assert character_skill is not None, "CharacterSkill not found."
        assert enemy is not None, "Enemy not found."
        assert monster is not None, "Linked Monster not found."

        # Dynamic Telegram ID.
        # Never hardcode a user's Telegram ID.
        telegram_id = character.telegram_id

        print("\n" + "=" * 80)
        print("👤 CHARACTER")
        print("-" * 80)

        print(f"ID={character.id}")
        print(f"Name={character.name}")
        print(f"Level={character.level}")
        print(f"HP={character.hp}/{character.max_hp}")
        print(f"Mana={character.mana}/{character.max_mana}")

        print("\n" + "=" * 80)
        print("🔮 SKILL")
        print("-" * 80)

        print(f"Name={skill.name}")
        print(f"Skill ID={skill.id}")
        print(f"Skill Level={character_skill.level}")
        print(f"Base Power={skill.base_power}")
        print(f"Power Per Level={skill.power_per_level}")
        print(f"Mana Cost={skill.mana_cost}")

        print("\n" + "=" * 80)
        print("👹 ENEMY")
        print("-" * 80)

        print(f"ID={enemy.id}")
        print(f"Name={enemy.name}")
        print(f"Monster ID={monster.id}")
        print(f"Monster Variant={monster.variant}")
        print(f"Element={monster.element}")

    # ========================================================
    # SAVE ORIGINAL DATABASE STATE
    # ========================================================

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.id == TEST_CHARACTER_ID
            )
        )

        character_skill = await session.scalar(
            select(CharacterSkill).where(
                CharacterSkill.character_id == TEST_CHARACTER_ID,
                CharacterSkill.skill_id == TEST_SKILL_ID,
            )
        )

        assert character is not None
        assert character_skill is not None

        original_character = {
            "level": character.level,
            "xp": character.xp,
            "skill_xp": character.skill_xp,
            "gold": character.gold,
            "hp": character.hp,
            "max_hp": character.max_hp,
            "mana": character.mana,
            "max_mana": character.max_mana,
        }

        original_skill = {
            "level": character_skill.level,
            "slot": character_skill.slot,
            "unlocked": character_skill.unlocked,
        }

    try:

        # ====================================================
        # PREPARE TEST STATE
        # ====================================================

        print("\n" + "=" * 80)
        print("🧪 PREPARING COMBAT TEST STATE")
        print("-" * 80)

        async with AsyncSessionLocal() as session:

            character = await session.scalar(
                select(Character).where(
                    Character.id == TEST_CHARACTER_ID
                )
            )

            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == TEST_CHARACTER_ID,
                    CharacterSkill.skill_id == TEST_SKILL_ID,
                )
            )

            assert character is not None
            assert character_skill is not None

            character_skill.level = 3
            character_skill.unlocked = True
            character_skill.slot = 1

            character.hp = character.max_hp
            character.mana = character.max_mana

            await session.commit()

        print("Skill Level=3")
        print("Skill unlocked=True")
        print("Character HP restored.")
        print("Character Mana restored.")
        print("✅ Combat test state prepared.")

        # ====================================================
        # TEST 1 - CREATE BATTLE
        # ====================================================

        print("\n" + "=" * 80)
        print("🧪 TEST 1 - CREATE BATTLE")
        print("-" * 80)

        success, message, battle = await create_battle(
            telegram_id,
            TEST_ENEMY_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")

        assert success is True
        assert battle is not None

        battle_id = battle["battle_id"]

        print(f"Battle ID={battle_id}")

        print(
            f"Player HP="
            f"{battle['player_hp']}/"
            f"{battle['player_max_hp']}"
        )

        print(
            f"Player Mana="
            f"{battle['player_mana']}/"
            f"{battle['player_max_mana']}"
        )

        print(
            f"Enemy HP="
            f"{battle['enemy_hp']}/"
            f"{battle['enemy_max_hp']}"
        )

        assert battle["telegram_id"] == telegram_id
        assert battle["player_hp"] > 0
        assert battle["player_mana"] > 0
        assert battle["enemy_hp"] > 0

        print("✅ Battle created successfully.")

        # ====================================================
        # TEST 2 - INITIAL BATTLE STATE
        # ====================================================

        print("\n" + "=" * 80)
        print("🧪 TEST 2 - INITIAL BATTLE STATE")
        print("-" * 80)

        loaded_battle = await get_battle(
            battle_id
        )

        assert loaded_battle is not None

        before_mana = loaded_battle["player_mana"]
        before_enemy_hp = loaded_battle["enemy_hp"]

        print(f"Player Mana Before={before_mana}")
        print(f"Enemy HP Before={before_enemy_hp}")

        assert before_mana > 0
        assert before_enemy_hp > 0

        print("✅ Initial battle state is valid.")

        # ====================================================
        # TEST 3 - SKILL MANA COST
        # ====================================================

        print("\n" + "=" * 80)
        print("🧪 TEST 3 - SKILL MANA COST")
        print("-" * 80)

        expected_mana_cost = get_skill_mana_cost(
            skill,
            3,
        )

        print(
            f"Expected Mana Cost="
            f"{expected_mana_cost}"
        )

        assert expected_mana_cost > 0

        print("✅ Skill Mana Cost is valid.")

        # ====================================================
        # TEST 4 - PLAYER USES SKILL
        # ====================================================

        print("\n" + "=" * 80)
        print("🧪 TEST 4 - PLAYER USES SKILL")
        print("-" * 80)

        (
            success,
            message,
            damage,
            victory,
            updated_battle,
        ) = await player_skill(
            battle_id,
            TEST_SKILL_ID,
        )

        print(f"Success={success}")
        print(f"Message={message}")
        print(f"Damage={damage}")
        print(f"Victory={victory}")

        assert success is True
        assert updated_battle is not None
        assert damage > 0

        print(
            f"Mana After="
            f"{updated_battle['player_mana']}"
        )

        print(
            f"Enemy HP After="
            f"{updated_battle['enemy_hp']}"
        )

        # ----------------------------------------------------
        # Mana validation
        # ----------------------------------------------------

        expected_mana_after = (
            before_mana
            - expected_mana_cost
        )

        assert (
            updated_battle["player_mana"]
            == expected_mana_after
        )

        # ----------------------------------------------------
        # Enemy HP validation
        # ----------------------------------------------------

        expected_enemy_hp = (
            before_enemy_hp
            - damage
        )

        assert (
            updated_battle["enemy_hp"]
            == max(0, expected_enemy_hp)
        )

        print(
            "✅ Skill Mana consumption is correct."
        )

        print(
            "✅ Skill Damage was applied correctly."
        )

        # ====================================================
        # TEST 5 - DAMAGE VALIDATION
        # ====================================================

        print("\n" + "=" * 80)
        print("🧪 TEST 5 - DAMAGE VALIDATION")
        print("-" * 80)

        assert damage >= 1

        assert updated_battle["enemy_hp"] >= 0

        assert (
            updated_battle["enemy_hp"]
            <= before_enemy_hp
        )

        print(f"Skill Damage={damage}")

        print(
            f"Enemy HP: "
            f"{before_enemy_hp} -> "
            f"{updated_battle['enemy_hp']}"
        )

        print("✅ Damage result is valid.")

        # ====================================================
        # TEST 6 - SKILL OWNERSHIP / LEVEL
        # ====================================================

        print("\n" + "=" * 80)
        print("🧪 TEST 6 - SKILL STATE VALIDATION")
        print("-" * 80)

        character_skill_result = await get_character_skill(
            TEST_CHARACTER_ID,
            TEST_SKILL_ID,
        )

        assert character_skill_result is not None

        # get_character_skill returns:
        # (Skill, CharacterSkill)

        skill_obj, current_character_skill = (
            character_skill_result
        )

        assert skill_obj.id == TEST_SKILL_ID

        assert (
            current_character_skill.skill_id
            == TEST_SKILL_ID
        )

        assert (
            current_character_skill.unlocked
            is True
        )

        assert (
            current_character_skill.level
            == 3
        )

        print(
            f"Skill ID="
            f"{skill_obj.id}"
        )

        print(
            f"Skill Level="
            f"{current_character_skill.level}"
        )

        print(
            f"Unlocked="
            f"{current_character_skill.unlocked}"
        )

        print(
            "✅ Skill ownership and level "
            "remained correct."
        )

        # ====================================================
        # TEST 7 - BATTLE PERSISTENCE
        # ====================================================

        print("\n" + "=" * 80)
        print("🧪 TEST 7 - BATTLE PERSISTENCE")
        print("-" * 80)

        persisted_battle = await get_battle(
            battle_id
        )

        assert persisted_battle is not None

        print(
            f"Persisted Player Mana="
            f"{persisted_battle['player_mana']}"
        )

        print(
            f"Persisted Enemy HP="
            f"{persisted_battle['enemy_hp']}"
        )

        assert (
            persisted_battle["player_mana"]
            == updated_battle["player_mana"]
        )

        assert (
            persisted_battle["enemy_hp"]
            == updated_battle["enemy_hp"]
        )

        print(
            "✅ Battle state persisted correctly."
        )

        # ====================================================
        # TEST 8 - ACTIVE BATTLE DETECTION
        # ====================================================

        print("\n" + "=" * 80)
        print("🧪 TEST 8 - ACTIVE BATTLE DETECTION")
        print("-" * 80)

        active = await has_active_battle(
            telegram_id
        )

        print(
            f"Has Active Battle={active}"
        )

        assert active is True

        print(
            "✅ Active battle correctly detected."
        )

        # ====================================================
        # TEST 9 - CLEANUP
        # ====================================================

        print("\n" + "=" * 80)
        print("🧪 TEST 9 - BATTLE CLEANUP")
        print("-" * 80)

        await finish_battle(
            battle_id
        )

        active_after = await has_active_battle(
            telegram_id
        )

        print(
            f"Has Active Battle After Cleanup="
            f"{active_after}"
        )

        assert active_after is False

        print(
            "✅ Battle cleanup completed."
        )

        battle_id = None

    finally:

        # ====================================================
        # FINAL BATTLE CLEANUP
        # ====================================================

        if battle_id is not None:

            try:
                await finish_battle(
                    battle_id
                )
            except Exception:
                pass

        # ====================================================
        # RESTORE DATABASE
        # ====================================================

        print("\n" + "=" * 80)
        print("🧹 RESTORING DATABASE")
        print("-" * 80)

        async with AsyncSessionLocal() as session:

            character = await session.scalar(
                select(Character).where(
                    Character.id == TEST_CHARACTER_ID
                )
            )

            character_skill = await session.scalar(
                select(CharacterSkill).where(
                    CharacterSkill.character_id
                    == TEST_CHARACTER_ID,
                    CharacterSkill.skill_id
                    == TEST_SKILL_ID,
                )
            )

            if character is not None:

                character.level = (
                    original_character["level"]
                )

                character.xp = (
                    original_character["xp"]
                )

                character.skill_xp = (
                    original_character["skill_xp"]
                )

                character.gold = (
                    original_character["gold"]
                )

                character.hp = (
                    original_character["hp"]
                )

                character.max_hp = (
                    original_character["max_hp"]
                )

                character.mana = (
                    original_character["mana"]
                )

                character.max_mana = (
                    original_character["max_mana"]
                )

            if character_skill is not None:

                character_skill.level = (
                    original_skill["level"]
                )

                character_skill.slot = (
                    original_skill["slot"]
                )

                character_skill.unlocked = (
                    original_skill["unlocked"]
                )

            await session.commit()

        print("✅ Database state restored.")

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print("\n" + "=" * 80)
    print("🎉 ALL SKILL COMBAT INTEGRATION TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())