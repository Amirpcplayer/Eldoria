from __future__ import annotations

from database.redis import redis

DELEGATED_ADMIN_SET = "world_eldoria:delegated_admins"


async def is_delegated_admin(telegram_id: int) -> bool:
    try:
        return bool(await redis.sismember(DELEGATED_ADMIN_SET, str(telegram_id)))
    except Exception:
        return False


async def add_delegated_admin(telegram_id: int) -> None:
    await redis.sadd(DELEGATED_ADMIN_SET, str(telegram_id))


async def list_delegated_admins() -> list[int]:
    values = await redis.smembers(DELEGATED_ADMIN_SET)
    result = []
    for value in values:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return sorted(set(result))
