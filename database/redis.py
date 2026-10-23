from redis.asyncio import Redis

from config.settings import settings


redis = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    max_connections=settings.redis_max_connections,
    socket_timeout=settings.redis_socket_timeout,
    socket_connect_timeout=settings.redis_connect_timeout,
    health_check_interval=settings.redis_health_check_interval,
)
