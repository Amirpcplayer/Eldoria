from services.power_service import get_hero_base_stats
from services.xp_service import get_base_stats_for_level
from services.skill_service import get_skill_power
from types import SimpleNamespace


def test_level_100_power_curve_matches_xp_service():
    combat = get_hero_base_stats(100)
    xp = get_base_stats_for_level(100)
    assert combat.hp == xp["max_hp"] == 490150
    assert combat.mana == xp["max_mana"] == 490150
    assert combat.attack == xp["attack"] == 49995
    assert combat.magic_power == xp["magic_power"] == 49995
    assert combat.defense == xp["defense"] == 25000
    assert combat.magic_defense == xp["magic_defense"] == 25000


def test_level_one_stats_remain_starter_friendly():
    combat = get_hero_base_stats(1)
    xp = get_base_stats_for_level(1)
    assert combat.hp == xp["max_hp"] == 100
    assert combat.attack == xp["attack"] == 10
    assert combat.defense == xp["defense"] == 8


def test_max_skill_intrinsic_power_is_not_double_counted_with_magic_stat():
    skill = SimpleNamespace(base_power=50, power_per_level=110)
    assert 14000 <= get_skill_power(skill, 200) <= 16000
