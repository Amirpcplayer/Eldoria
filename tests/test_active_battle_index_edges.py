from unittest.mock import AsyncMock

import pytest

import services.combat_service as combat_service


@pytest.mark.asyncio
async def test_active_battle_index_rejects_battle_owned_by_another_player(monkeypatch):
    index_key = combat_service.get_player_active_battle_key(42)
    monkeypatch.setattr(combat_service.redis, "get", AsyncMock(side_effect=["battle-123", "battle-123"]))
    monkeypatch.setattr(
        combat_service,
        "get_battle",
        AsyncMock(return_value={
            "battle_id": "battle-123",
            "telegram_id": 99,
            "player_hp": 100,
            "enemy_hp": 80,
        }),
    )
    delete = AsyncMock()
    monkeypatch.setattr(combat_service.redis, "delete", delete)

    result = await combat_service.get_active_battle_for_player(42)

    assert result is None
    delete.assert_awaited_once_with(index_key)


@pytest.mark.asyncio
async def test_active_battle_index_rejects_finished_battle(monkeypatch):
    index_key = combat_service.get_player_active_battle_key(42)
    monkeypatch.setattr(combat_service.redis, "get", AsyncMock(side_effect=["battle-123", "battle-123"]))
    monkeypatch.setattr(
        combat_service,
        "get_battle",
        AsyncMock(return_value={
            "battle_id": "battle-123",
            "telegram_id": 42,
            "player_hp": 0,
            "enemy_hp": 80,
        }),
    )
    delete = AsyncMock()
    monkeypatch.setattr(combat_service.redis, "delete", delete)

    result = await combat_service.get_active_battle_for_player(42)

    assert result is None
    delete.assert_awaited_once_with(index_key)
