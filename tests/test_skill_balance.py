from models.skill import Skill

from services.skill_service import (
    SKILL_MANA_GROWTH,
    SKILL_UPGRADE_COSTS,
    get_skill_mana_cost,
    get_skill_power,
)


def make_test_skill(
    *,
    name: str = "Test Skill",
    element: str = "fire",
    base_power: int = 50,
    power_per_level: int = 110,
    mana_cost: int = 50,
    max_level: int = 10,
) -> Skill:
    return Skill(
        name=name,
        description="Test skill",
        element=element,
        skill_type="magic",
        target_type="single",
        rarity="common",
        max_level=max_level,
        base_power=base_power,
        power_per_level=power_per_level,
        mana_cost=mana_cost,
        cooldown=5,
        unlock_level=1,
        is_active=True,
    )


def test_skill_progression():
    skill = make_test_skill()

    powers = [
        get_skill_power(skill, level)
        for level in range(1, 11)
    ]

    mana_costs = [
        get_skill_mana_cost(skill, level)
        for level in range(1, 11)
    ]

    assert len(powers) == 10
    assert len(mana_costs) == 10

    assert all(power > 0 for power in powers)
    assert all(mana > 0 for mana in mana_costs)

    assert powers == sorted(powers)
    assert mana_costs == sorted(mana_costs)

    assert powers[0] == 50
    assert powers[-1] == 725

    assert mana_costs[0] == 50
    assert mana_costs[-1] == 75


def test_power_formula():
    skill = make_test_skill(
        base_power=50,
        power_per_level=110,
    )

    for level in range(1, 11):
        expected = skill.base_power + ((level - 1) * max(75, int(skill.power_per_level * 0.65)))

        actual = get_skill_power(
            skill,
            level,
        )

        assert actual == expected


def test_mana_formula():
    for element, growth in SKILL_MANA_GROWTH.items():
        skill = make_test_skill(
            element=element,
            mana_cost=50,
        )

        for level in range(1, 11):
            expected = skill.mana_cost + int((level - 1) * growth * 0.35)

            actual = get_skill_mana_cost(
                skill,
                level,
            )

            assert actual == expected


def test_efficiency():
    skill = make_test_skill(
        base_power=50,
        power_per_level=110,
        mana_cost=50,
        element="fire",
    )

    efficiencies = []

    for level in range(1, 11):
        power = get_skill_power(
            skill,
            level,
        )

        mana = get_skill_mana_cost(
            skill,
            level,
        )

        assert power > 0
        assert mana > 0

        efficiency = power / mana

        assert efficiency > 0

        efficiencies.append(efficiency)

    first = efficiencies[0]
    last = efficiencies[-1]

    change = (last - first) / first

    # Efficiency must not collapse by more than 60%.
    assert change >= -0.60


def test_upgrade_costs():
    expected_costs = {
        1: {"xp": 500, "gold": 1000},
        2: {"xp": 1000, "gold": 2000},
        3: {"xp": 1500, "gold": 3500},
        4: {"xp": 2500, "gold": 5000},
        5: {"xp": 4000, "gold": 8000},
        6: {"xp": 6000, "gold": 12000},
        7: {"xp": 8500, "gold": 17000},
        8: {"xp": 12000, "gold": 24000},
        9: {"xp": 16000, "gold": 32000},
    }

    assert SKILL_UPGRADE_COSTS == expected_costs