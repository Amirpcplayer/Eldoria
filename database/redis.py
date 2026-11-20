"""Redis client configuration, including an in-process standalone backend."""

from redis.asyncio import Redis

from config.settings import settings


if settings.redis_url.strip().lower().startswith("memory://"):
    # The Windows standalone launcher has no Redis server. fakeredis provides
    # the Redis API in-process; the optional Lua extra is required by atomic
    # combat updates and scheduler leases used by the game.
    from fakeredis.aioredis import FakeRedis

    redis = FakeRedis(decode_responses=True)
else:
    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=settings.redis_max_connections,
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_connect_timeout,
        health_check_interval=settings.redis_health_check_interval,
    )
