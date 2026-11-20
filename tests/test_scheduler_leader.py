import asyncio

import pytest

from services import scheduler_leader


class FakeRedis:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def eval(self, script, numkeys, key, token, *args):
        self.calls.append((script, numkeys, key, token, args))
        return self.result


@pytest.mark.asyncio
async def test_lease_renewal_stops_when_worker_no_longer_owns_lease(monkeypatch):
    fake = FakeRedis(0)
    monkeypatch.setattr(scheduler_leader, "redis", fake)

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(scheduler_leader.asyncio, "sleep", no_wait)
    await scheduler_leader._maintain_lease("worker-token")

    assert len(fake.calls) == 1
    assert fake.calls[0][2:4] == (
        scheduler_leader.LEASE_KEY,
        "worker-token",
    )


@pytest.mark.asyncio
async def test_lease_renewal_stops_cleanly_when_redis_fails(monkeypatch):
    class BrokenRedis:
        async def eval(self, *args):
            raise RuntimeError("redis unavailable")

    monkeypatch.setattr(scheduler_leader, "redis", BrokenRedis())

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(scheduler_leader.asyncio, "sleep", no_wait)
    await scheduler_leader._maintain_lease("worker-token")
