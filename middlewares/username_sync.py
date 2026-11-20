# middlewares/username_sync.py

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.database import AsyncSessionLocal
from models.character import Character
from sqlalchemy import select


class UsernameSyncMiddleware(BaseMiddleware):
    """
    Username کاربر را در هر تعامل با ربات با دیتابیس همگام می‌کند.

    نکته:
    - هیچ Telegram IDای به صورت hardcode استفاده نمی‌شود.
    - فقط کاربری که واقعاً با ربات تعامل کرده بررسی می‌شود.
    - اگر username نداشته باشد، چیزی تغییر نمی‌کند.
    """

    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, dict[str, Any]],
            Awaitable[Any],
        ],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:

        from_user = getattr(event, "from_user", None)

        if from_user is not None:
            telegram_id = from_user.id
            telegram_username = from_user.username

            if telegram_username:
                normalized_username = telegram_username.strip().lstrip("@").lower()

                if normalized_username:
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(
                            select(Character).where(
                                Character.telegram_id == telegram_id
                            )
                        )

                        character = result.scalar_one_or_none()

                        if character is not None:
                            if character.telegram_username != normalized_username:
                                character.telegram_username = normalized_username
                                await session.commit()

        return await handler(event, data)