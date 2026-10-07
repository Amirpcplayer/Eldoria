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
from services.character_stats_service import calculate_character_combat_stats
from services.power_service import get_hero_base_stats


async def main():
    print("=" * 80)
    print("WORLD ELDORIA - LEVEL UP STATS TEST")
    print("=" * 80)

    # ------------------------------------------------------------------
    # LOAD CHARACTER
    # ------------------------------------------------------------------
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character)
            .order_by(Character.id)
            .limit(1)
        )

        if character is None:
            print("❌ هیچ کاراکتری در دیتابیس پیدا نشد.")
            return

        character_id = character.id
        character_name = character.name
        character_level = character.level
        character_xp = character.xp

    print("\n👤 CHARACTER")
    print("-" * 80)
    print(f"ID={character_id}")
    print(f"Name={character_name}")
    print(f"Level={character_level}")
    print(f"XP={character_xp}")

    # ------------------------------------------------------------------
    # EXPECTED BASE STATS
    # ------------------------------------------------------------------
    base = get_hero_base_stats(character_level)

    print("\n📈 EXPECTED BASE STATS")
    print("-" * 80)
    print(f"Level={character_level}")
    print(f"HP={base.hp}")
    print(f"Mana={base.mana}")
    print(f"ATK={base.attack}")
    print(f"Magic Power={base.magic_power}")
    print(f"DEF={base.defense}")
    print(f"MDEF={base.magic_defense}")
    print(f"Speed={base.speed}")
    print(f"Accuracy={base.accuracy}")
    print(f"Luck={base.luck}")
    print(f"Critical={base.critical}")

    # ------------------------------------------------------------------
    # REAL COMBAT STATS
    # ------------------------------------------------------------------
    combat = await calculate_character_combat_stats(character)

    print("\n⚔️ REAL COMBAT STATS")
    print("-" * 80)
    print(f"HP={combat.hp}/{combat.max_hp}")
    print(f"Mana={combat.mana}/{combat.max_mana}")
    print(f"ATK={combat.attack}")
    print(f"Magic Power={combat.magic_power}")
    print(f"DEF={combat.defense}")
    print(f"MDEF={combat.magic_defense}")
    print(f"Speed={combat.speed}")
    print(f"Accuracy={combat.accuracy}")
    print(f"Luck={combat.luck}")
    print(f"Critical={combat.critical}")

    # ------------------------------------------------------------------
    # BASE STAT VALIDATION
    # ------------------------------------------------------------------
    print("\n🧪 BASE STAT VALIDATION")
    print("-" * 80)

    checks = [
        ("HP", combat.max_hp >= base.hp),
        ("Mana", combat.max_mana >= base.mana),
        ("ATK", combat.attack >= base.attack),
        ("Magic Power", combat.magic_power >= base.magic_power),
        ("DEF", combat.defense >= base.defense),
        ("MDEF", combat.magic_defense >= base.magic_defense),
        ("Speed", combat.speed >= base.speed),
        ("Accuracy", combat.accuracy >= base.accuracy),
        ("Luck", combat.luck >= base.luck),
        ("Critical", combat.critical >= base.critical),
    ]

    all_passed = True

    for name, passed in checks:
        if passed:
            print(f"✅ {name}")
        else:
            print(f"❌ {name}")
            all_passed = False

    # ------------------------------------------------------------------
    # LEVEL GROWTH CHECK
    # ------------------------------------------------------------------
    if character_level > 1:
        previous = get_hero_base_stats(character_level - 1)
        current = get_hero_base_stats(character_level)

        print("\n📊 LEVEL GROWTH CHECK")
        print("-" * 80)

        growth_checks = [
            ("HP", previous.hp, current.hp),
            ("Mana", previous.mana, current.mana),
            ("ATK", previous.attack, current.attack),
            ("Magic Power", previous.magic_power, current.magic_power),
            ("DEF", previous.defense, current.defense),
            ("MDEF", previous.magic_defense, current.magic_defense),
            ("Speed", previous.speed, current.speed),
            ("Accuracy", previous.accuracy, current.accuracy),
            ("Luck", previous.luck, current.luck),
            ("Critical", previous.critical, current.critical),
        ]

        for name, old_value, new_value in growth_checks:
            if new_value >= old_value:
                print(
                    f"✅ {name}: "
                    f"Lv.{character_level - 1}={old_value} "
                    f"→ Lv.{character_level}={new_value}"
                )
            else:
                print(
                    f"❌ {name}: "
                    f"Lv.{character_level - 1}={old_value} "
                    f"→ Lv.{character_level}={new_value}"
                )
                all_passed = False

    # ------------------------------------------------------------------
    # DATABASE SAFETY CHECK
    # ------------------------------------------------------------------
    async with AsyncSessionLocal() as session:
        character_after = await session.scalar(
            select(Character).where(
                Character.id == character_id
            )
        )

        if character_after is None:
            print("\n❌ Character بعد از تست پیدا نشد.")
            all_passed = False
        else:
            database_unchanged = (
                character_after.level == character_level
                and character_after.xp == character_xp
            )

            print("\n🛡️ DATABASE SAFETY CHECK")
            print("-" * 80)

            if database_unchanged:
                print("✅ Level تغییر نکرد.")
                print("✅ XP تغییر نکرد.")
            else:
                print("❌ اطلاعات Character تغییر کرده است.")
                all_passed = False

    # ------------------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)

    if all_passed:
        print("✅ LEVEL UP STATS TEST COMPLETED")
        print("✅ قدرت Combat بر اساس Level به‌درستی محاسبه می‌شود.")
        print("✅ رشد Stats بین Levelها صحیح است.")
        print("✅ تست هیچ اطلاعاتی در دیتابیس را تغییر نداد.")
    else:
        print("❌ LEVEL UP STATS TEST FAILED")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())