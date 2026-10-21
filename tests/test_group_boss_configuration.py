"""Regression checks for boss configuration and the solo-story cooldown."""
from __future__ import annotations
import ast
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BOSS_SOURCE = ROOT / "handlers" / "group_boss.py"
PVP_SOURCE = ROOT / "handlers" / "pvp.py"
def _literal_assignments():
    tree = ast.parse(BOSS_SOURCE.read_text(encoding="utf-8"))
    wanted = {"BOSS_POOL", "BOSS_ATTACK_FAMILIES"}
    found = {}
    for node in tree.body:
        targets, value = [], None
        if isinstance(node, ast.Assign): targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign): targets, value = [node.target], node.value
        for target in targets:
            if isinstance(target, ast.Name) and target.id in wanted:
                found[target.id] = ast.literal_eval(value)
    return found
def test_all_50_bosses_use_the_single_plural_image_directory():
    bosses = _literal_assignments()["BOSS_POOL"]
    assert len(bosses) == 50
    assert len({boss["key"] for boss in bosses}) == 50
    assert all(boss["image"].startswith("assets/bosses/") for boss in bosses)
    assert all("assets/boss/" not in boss["image"] for boss in bosses)
def test_each_boss_attack_family_has_five_distinct_moves_and_damage_multipliers():
    families = _literal_assignments()["BOSS_ATTACK_FAMILIES"]
    assert len(families) == 50
    for name, attacks in families.items():
        assert len(attacks) >= 5, name
        assert len({move["name"] for move in attacks}) >= 5, name
        assert len({move["multiplier"] for move in attacks}) >= 4, name
def test_story_cooldown_and_repeat_message_are_configured():
    source = PVP_SOURCE.read_text(encoding="utf-8")
    assert "STORY_COOLDOWN_SECONDS = 5 * 60" in source
    assert "فعلاً خطری شما را تهدید نمی‌کند" in source
    assert "group_story_attack_text" in source and "group_story_magic_text" in source
