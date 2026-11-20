"""Opt-in Redis concurrency benchmark for an isolated staging Redis.

This is a Redis microbenchmark, not a Telegram bot or 500-player load test.
Set ELDORIA_BENCHMARK_REDIS_URL to a disposable staging instance and pass
--confirm-isolated-redis before running it.
"""
from __future__ import annotations

import argparse
import asyncio
import math
import os
import statistics
import time
import uuid

from redis.asyncio import Redis


def percentile(values: list[float], fraction: float) -> float:
    """Return the nearest-rank percentile (fraction is in the 0..1 range)."""
    if not 0 <= fraction <= 1:
        raise ValueError("fraction must be between 0 and 1")
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


async def benchmark(redis: Redis, concurrency: int, operations: int) -> dict[str, float]:
    if concurrency < 1 or concurrency > 500:
        raise ValueError("concurrency must be between 1 and 500")
    if operations < 1:
        raise ValueError("operations must be positive")

    run_id = uuid.uuid4().hex
    latencies_ms: list[float] = []
    per_worker = (operations + concurrency - 1) // concurrency

    async def worker(worker_id: int) -> None:
        local: list[float] = []
        for sequence in range(per_worker):
            key = f"eldoria:benchmark:{run_id}:{worker_id}:{sequence}"
            started = time.perf_counter()
            await redis.set(key, "1", ex=120)
            await redis.get(key)
            local.append((time.perf_counter() - started) * 1000)
        latencies_ms.extend(local)

    elapsed = 0.0
    try:
        started = time.perf_counter()
        await asyncio.gather(*(worker(i) for i in range(concurrency)))
        # Measure workload only; cleanup latency must not distort throughput.
        elapsed = time.perf_counter() - started
    finally:
        # Only scan this unique run namespace. TTL is a fallback if cleanup fails.
        cursor = 0
        pattern = f"eldoria:benchmark:{run_id}:*"
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=500)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break

    count = len(latencies_ms)
    return {
        "concurrency": float(concurrency),
        "operations": float(count),
        "seconds": elapsed,
        "ops_per_second": count / elapsed if elapsed else 0.0,
        "p50_ms": percentile(latencies_ms, 0.50),
        "p95_ms": percentile(latencies_ms, 0.95),
        "p99_ms": percentile(latencies_ms, 0.99),
        "mean_ms": statistics.fmean(latencies_ms) if latencies_ms else 0.0,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-isolated-redis",
        action="store_true",
        help="Required acknowledgement: the target must be disposable staging Redis.",
    )
    parser.add_argument(
        "--operations",
        type=int,
        default=2000,
        help="Approximate SET+GET pairs per concurrency level (default: 2000).",
    )
    parser.add_argument(
        "--levels",
        default="1,10,50,100,500",
        help="Comma-separated concurrency levels (default: 1,10,50,100,500).",
    )
    args = parser.parse_args()

    url = os.getenv("ELDORIA_BENCHMARK_REDIS_URL", "").strip()
    if not args.confirm_isolated_redis:
        parser.error("refusing to run without --confirm-isolated-redis")
    if not url:
        parser.error("set ELDORIA_BENCHMARK_REDIS_URL to a disposable staging Redis URL")
    if args.operations < 1:
        parser.error("--operations must be positive")

    try:
        levels = [int(value.strip()) for value in args.levels.split(",")]
    except ValueError:
        parser.error("--levels must be comma-separated positive integers")
    if not levels or any(level < 1 or level > 500 for level in levels):
        parser.error("--levels values must be between 1 and 500")
    if len(set(levels)) != len(levels):
        parser.error("--levels must not contain duplicates")

    client = Redis.from_url(url, decode_responses=True, socket_timeout=5)
    try:
        await client.ping()
        print("Redis microbenchmark; target connection succeeded.")
        print("concurrency | pairs | seconds | pairs/s | p50 ms | p95 ms | p99 ms")
        for level in levels:
            result = await benchmark(client, level, args.operations)
            print(
                f"{int(result['concurrency']):11d} | "
                f"{int(result['operations']):5d} | "
                f"{result['seconds']:7.3f} | "
                f"{result['ops_per_second']:7.1f} | "
                f"{result['p50_ms']:6.2f} | "
                f"{result['p95_ms']:6.2f} | "
                f"{result['p99_ms']:6.2f}"
            )
        print("Note: this measures Redis SET+GET latency only, not application capacity.")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
