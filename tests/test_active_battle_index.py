from unittest.mock import AsyncMock

import pytest

import services.combat_service as combat_service


@pytest.mark.asyncio
async def test_active_battle_lookup_uses_player_index(monkeypatch):
    battle = {
        "battle_id": "battle-123",
        "telegram_id": 42,
        "player_hp": 100,
        "enemy_hp": 80,
    }
    redis_get = AsyncMock(return_value="battle-123")
    get_battle = AsyncMock(return_value=battle)
    scan_iter = AsyncMock()

    monkeypatch.setattr(combat_service.redis, "get", redis_get)
    monkeypatch.setattr(combat_service, "get_battle", get_battle)
    monkeypatch.setattr(combat_service.redis, "scan_iter", scan_iter)

    result = await combat_service.get_active_battle_for_player(42)

    assert result == battle
    redis_get.assert_awaited_once_with(combat_service.get_player_active_battle_key(42))
    get_battle.assert_awaited_once_with("battle-123")
    scan_iter.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_active_battle_index_is_removed(monkeypatch):
    redis_get = AsyncMock(return_value="stale-battle")
    redis_delete = AsyncMock()
    get_battle = AsyncMock(return_value=None)

    monkeypatch.setattr(combat_service.redis, "get", redis_get)
    monkeypatch.setattr(combat_service.redis, "delete", redis_delete)
    monkeypatch.setattr(combat_service, "get_battle", get_battle)

    result = await combat_service.get_active_battle_for_player(42)

    assert result is None
    assert redis_get.await_count == 3
    redis_delete.assert_awaited_once_with(combat_service.get_player_active_battle_key(42))
