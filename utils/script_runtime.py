"""Shared CLI lifecycle for database maintenance scripts (place in utils/)."""
from __future__ import annotations

import asyncio
import logging


def run_script(function, *args):
    """Dispose the engine on the same event loop, including on failure."""
    async def run():
        from database.database import engine

        try:
            return await function(*args)
        finally:
            try:
                await engine.dispose()
            except Exception:
                logging.getLogger(__name__).exception("Database engine cleanup failed")

    return asyncio.run(run())
