"""Opt-in Redis concurrency benchmark for an isolated staging Redis.

This is a Redis microbenchmark, not a Telegram bot or 500-player load test.
Set ELDORIA_BENCHMARK_REDIS_URL to a disposable staging instance and pass
--confirm-isolated-redis before running it.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import time
import uuid

from redis.asyncio import Redis


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return ordered[index]


async def benchmark(redis: Redis, concurrency: int, operations: int) -> dict[str, float]:
    run_id = uuid.uuid4().hex
    latencies_ms: list[float] = []
    latency_lock = asyncio.Lock()
    per_worker = (operations + concurrency - 1) // concurrency

    async def worker(worker_id: int) -> None:
        local: list[float] = []
        for sequence in range(per_worker):
            key = f"eldoria:benchmark:{run_id}:{worker_id}:{sequence}"
            started = time.perf_counter()
            await redis.set(key, "1", ex=120)
            await redis.get(key)
            local.append((time.perf_counter() - started) * 1000)
        async with latency_lock:
            latencies_ms.extend(local)

    started = time.perf_counter()
    try:
        await asyncio.gather(*(worker(i) for i in range(concurrency)))
    finally:
        # Keys expire automatically; scan only this unique benchmark namespace
        # so interrupted runs can be cleaned without touching application keys.
        cursor = 0
        pattern = f"eldoria:benchmark:{run_id}:*"
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=500)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break

    elapsed = time.perf_counter() - started
    return {
        "concurrency": float(concurrency),
        "operations": float(len(latencies_ms)),
        "seconds": elapsed,
        "ops_per_second": len(latencies_ms) / elapsed if elapsed else 0.0,
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
        help="Required safety acknowledgement: the target must be disposable staging Redis.",
    )
    parser.add_argument("--operations", type=int, default=2000,
                        help="Approximate SET+GET pairs per concurrency level (default: 2000).")
    parser.add_argument("--levels", default="1,10,50,100,500",
                        help="Comma-separated concurrency levels (default: 1,10,50,100,500).")
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
