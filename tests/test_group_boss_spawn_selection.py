"""Regression tests for the randomized group-boss spawn selection."""
import random
import unittest

from handlers.group_boss import BOSS_POOL, choose_boss_spawn


class GroupBossSpawnSelectionTests(unittest.TestCase):
    def test_pool_contains_50_unique_bosses(self):
        self.assertEqual(len(BOSS_POOL), 50)
        self.assertEqual(len({boss["key"] for boss in BOSS_POOL}), 50)

    def test_spawn_varies_boss_and_level(self):
        random.seed(20261011)
        results = [choose_boss_spawn() for _ in range(250)]
        self.assertGreater(len({boss["key"] for boss, _ in results}), 35)
        levels = {level for _, level in results}
        self.assertGreater(len(levels), 20)
        self.assertTrue(all(1 <= level <= 200 for _, level in results))

    def test_immediately_previous_boss_is_avoided(self):
        random.seed(20261011)
        previous = BOSS_POOL[0]["key"]
        for _ in range(100):
            boss, level = choose_boss_spawn(previous)
            self.assertNotEqual(boss["key"], previous)
            self.assertTrue(1 <= level <= 200)

    def test_low_levels_are_more_common_than_high_levels(self):
        random.seed(20261011)
        levels = [choose_boss_spawn()[1] for _ in range(2000)]
        low = sum(level <= 50 for level in levels)
        high = sum(level > 150 for level in levels)
        self.assertGreater(low, high * 2)


if __name__ == "__main__":
    unittest.main()
