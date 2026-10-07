from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.monster import Monster
from services.monster_data import MONSTER_FAMILIES


RESISTANCE_FIELDS = {
    "fire": "fire_resistance",
    "water": "water_resistance",
    "ice": "ice_resistance",
    "earth": "earth_resistance",
    "wind": "wind_resistance",
    "electro": "electro_resistance",
    "shadow": "shadow_resistance",
    "light": "light_resistance",
    "blood": "blood_resistance",
    "steel": "steel_resistance",
}


async def seed_monsters() -> int:
    processed = 0

    async with AsyncSessionLocal() as session:

        for family, variants in MONSTER_FAMILIES.items():

            for variant in variants:

                monster = await session.scalar(
                    select(Monster).where(
                        Monster.variant == variant.key
                    )
                )

                if monster is None:

                    monster = Monster(
                        family=family,
                        variant=variant.key,
                        name=variant.name,
                        description=variant.description,
                        tier=variant.tier,
                        power_multiplier=variant.power_multiplier,
                        element=variant.element,

                        base_hp=variant.base_hp,
                        base_attack=variant.base_attack,
                        base_magic_power=variant.base_magic_power,
                        base_defense=variant.base_defense,
                        base_magic_defense=variant.base_magic_defense,
                        base_speed=variant.base_speed,
                        base_accuracy=variant.base_accuracy,
                        base_luck=variant.base_luck,
                        base_critical=variant.base_critical,
                    )

                    session.add(monster)

                else:

                    monster.family = family
                    monster.name = variant.name
                    monster.description = variant.description
                    monster.tier = variant.tier
                    monster.power_multiplier = variant.power_multiplier
                    monster.element = variant.element

                    monster.base_hp = variant.base_hp
                    monster.base_attack = variant.base_attack
                    monster.base_magic_power = variant.base_magic_power
                    monster.base_defense = variant.base_defense
                    monster.base_magic_defense = variant.base_magic_defense
                    monster.base_speed = variant.base_speed
                    monster.base_accuracy = variant.base_accuracy
                    monster.base_luck = variant.base_luck
                    monster.base_critical = variant.base_critical

                for element, field_name in RESISTANCE_FIELDS.items():

                    setattr(
                        monster,
                        field_name,
                        variant.resistances.get(
                            element,
                            0.0,
                        ),
                    )

                processed += 1

        await session.commit()

    return processed