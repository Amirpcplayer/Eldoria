import pytest
from pydantic import ValidationError

from config.settings import Settings


def make_settings(**overrides):
    values = {
        "bot_token": "123456:TEST_TOKEN",
        "database_url": "postgresql+asyncpg://test:test@localhost/test",
        "redis_url": "redis://localhost:6379/0",
        "admin_id": 1,
    }
    values.update(overrides)
    return Settings(**values)


def test_pool_settings_have_safe_defaults():
    settings = make_settings()

    assert settings.db_pool_size == 5
    assert settings.db_max_overflow == 5
    assert settings.redis_max_connections == 50
    assert settings.redis_socket_timeout == 5.0
    assert settings.redis_connect_timeout == 5.0
    assert settings.slow_db_query_ms == 250
    assert settings.slow_update_ms == 1500


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("db_pool_size", 0),
        ("db_pool_size", 51),
        ("db_max_overflow", -1),
        ("db_pool_timeout", 0),
        ("db_pool_recycle", 59),
        ("redis_max_connections", 9),
        ("redis_max_connections", 501),
        ("redis_socket_timeout", 0),
        ("redis_connect_timeout", 61),
        ("slow_db_query_ms", 0),
        ("slow_update_ms", 60001),
    ],
)
def test_pool_settings_reject_unsafe_values(field, value):
    with pytest.raises(ValidationError):
        make_settings(**{field: value})


def test_pool_settings_allow_zero_redis_health_check_interval():
    settings = make_settings(redis_health_check_interval=0)

    assert settings.redis_health_check_interval == 0
