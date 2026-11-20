from __future__ import annotations

from aiogram import BaseMiddleware


class DeleteMainMenuOnClickMiddleware(BaseMiddleware):
    """Keep the clicked menu available for in-place panel editing.

    Ownership validation remains the responsibility of PanelOwnerMiddleware.
    """

    async def __call__(self, handler, event, data):
        return await handler(event, data)
