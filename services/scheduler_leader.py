from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable, Sequence

from database.redis import redis

logger = logging.getLogger(__name__)

LEASE_KEY = "eldoria:scheduler_leader"
LEASE_SECONDS = 45
RENEW_INTERVAL_SECONDS = 15
RETRY_INTERVAL_SECONDS = 5

SchedulerFactory = Callable[[], Awaitable[None]]

_RENEW_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('expire', KEYS[1], ARGV[2])
end
return 0
"""
_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


async def _maintain_lease(token: str) -> None:
    """Renew the lease until Redis rejects ownership or an error occurs."""
    while True:
        await asyncio.sleep(RENEW_INTERVAL_SECONDS)
        try:
            renewed = await redis.eval(
                _RENEW_SCRIPT, 1, LEASE_KEY, token, LEASE_SECONDS
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduler leader lease renewal failed")
            return
        if not renewed:
            logger.warning("Scheduler leader lease was lost")
            return


async def run_schedulers_as_leader(
    scheduler_factories: Sequence[SchedulerFactory],
) -> None:
    """Run periodic jobs on one Redis-elected worker, with lease renewal."""
    while True:
        token = str(uuid.uuid4())
        try:
            acquired = await redis.set(
                LEASE_KEY, token, nx=True, ex=LEASE_SECONDS
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Could not acquire scheduler leader lease")
            await asyncio.sleep(RETRY_INTERVAL_SECONDS)
            continue

        if not acquired:
            await asyncio.sleep(RETRY_INTERVAL_SECONDS)
            continue

        logger.info("This worker acquired the scheduler leader lease")
        jobs = [
            asyncio.create_task(factory(), name=f"eldoria-scheduled-job-{index}")
            for index, factory in enumerate(scheduler_factories, start=1)
        ]
        heartbeat = asyncio.create_task(
            _maintain_lease(token), name="eldoria-scheduler-lease-renewal"
        )
        try:
            done, _ = await asyncio.wait(
                [*jobs, heartbeat], return_when=asyncio.FIRST_COMPLETED
            )
            if heartbeat in done:
                logger.warning("Stopping scheduled jobs because leader lease ended")
            else:
                for task in done:
                    if task is not heartbeat:
                        error = task.exception() if not task.cancelled() else None
                        logger.error(
                            "A scheduler task stopped unexpectedly (task=%s, error=%r)",
                            task.get_name(),
                            error,
                        )
        except asyncio.CancelledError:
            raise
        finally:
            heartbeat.cancel()
            for task in jobs:
                task.cancel()
            await asyncio.gather(heartbeat, *jobs, return_exceptions=True)
            try:
                await redis.eval(_RELEASE_SCRIPT, 1, LEASE_KEY, token)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Could not release scheduler leader lease")

        await asyncio.sleep(RETRY_INTERVAL_SECONDS)
