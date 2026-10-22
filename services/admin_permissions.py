from __future__ import annotations

from database.redis import redis

FANART_ADMIN_SET = "world_eldoria:fanart_admins"


async def is_fanart_admin(telegram_id: int) -> bool:
    try:
        return bool(await redis.sismember(FANART_ADMIN_SET, str(telegram_id)))
    except Exception:
        return False


async def add_fanart_admin(telegram_id: int) -> None:
    await redis.sadd(FANART_ADMIN_SET, str(telegram_id))


async def list_fanart_admins() -> list[int]:
    values = await redis.smembers(FANART_ADMIN_SET)
    result = []
    for value in values:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return sorted(set(result))
