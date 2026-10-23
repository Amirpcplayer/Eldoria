from unittest.mock import AsyncMock

import pytest

import services.combat_service as combat_service


@pytest.mark.asyncio
async def test_create_battle_rejects_concurrent_request(monkeypatch):
    redis_set = AsyncMock(return_value=None)
    create_unlocked = AsyncMock()
    redis_eval = AsyncMock()

    monkeypatch.setattr(combat_service.redis, "set", redis_set)
    monkeypatch.setattr(combat_service.redis, "eval", redis_eval)
    monkeypatch.setattr(combat_service, "_create_battle_unlocked", create_unlocked)

    result = await combat_service.create_battle(123, 7)

    assert result[0] is False
    assert result[2] is None
    assert "در حال پردازش" in result[1]
    redis_set.assert_awaited_once()
    create_unlocked.assert_not_awaited()
    redis_eval.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_battle_releases_only_its_own_lock(monkeypatch):
    redis_set = AsyncMock(return_value=True)
    redis_eval = AsyncMock(return_value=1)
    create_unlocked = AsyncMock(return_value=(True, "ok", {"battle_id": "abc"}))

    monkeypatch.setattr(combat_service.redis, "set", redis_set)
    monkeypatch.setattr(combat_service.redis, "eval", redis_eval)
    monkeypatch.setattr(combat_service, "_create_battle_unlocked", create_unlocked)

    result = await combat_service.create_battle(123, 7)

    assert result == (True, "ok", {"battle_id": "abc"})
    create_unlocked.assert_awaited_once_with(123, 7)
    redis_eval.assert_awaited_once()
    args = redis_eval.await_args.args
    assert args[1] == 1
    assert args[2] == "eldoria:battle_create_lock:123"
    assert args[3]

# CI trigger: keep this focused regression suite attached to the integration PR.
