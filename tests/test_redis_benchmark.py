"""Unit tests for the Redis benchmark's percentile calculation."""
import unittest

from scripts.benchmark_redis_concurrency import percentile


class PercentileTests(unittest.TestCase):
    def test_nearest_rank_percentiles(self):
        values = [40.0, 10.0, 30.0, 20.0]
        self.assertEqual(percentile(values, 0.50), 20.0)
        self.assertEqual(percentile(values, 0.95), 40.0)
        self.assertEqual(percentile(values, 0.99), 40.0)

    def test_empty_input_returns_zero(self):
        self.assertEqual(percentile([], 0.95), 0.0)

    def test_fraction_boundaries(self):
        self.assertEqual(percentile([2.0, 1.0], 0.0), 1.0)
        self.assertEqual(percentile([2.0, 1.0], 1.0), 2.0)

    def test_invalid_fraction_raises(self):
        with self.assertRaises(ValueError):
            percentile([1.0], 1.1)


if __name__ == "__main__":
    unittest.main()
