from handlers.group_boss import BOSS_POOL, boss_attack_family

def test_all_50_bosses_have_at_least_five_attacks():
    assert len(BOSS_POOL) == 50
    for boss in BOSS_POOL:
        attacks = boss_attack_family(boss["key"])
        assert len(attacks) >= 5, boss["key"]
        assert len({a["name"] for a in attacks}) >= 5, boss["key"]
        assert len({a["multiplier"] for a in attacks}) >= 4, boss["key"]

def test_storm_harpy_does_not_use_generic_fist_attack():
    attacks = boss_attack_family("storm_harpy")
    names = {a["name"] for a in attacks}
    assert "صاعقهٔ بال‌ها" in names
    assert all("مشت" not in str(a["story"]) for a in attacks)
