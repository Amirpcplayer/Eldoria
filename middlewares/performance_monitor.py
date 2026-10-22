from __future__ import annotations

import logging
import time

from aiogram import BaseMiddleware
from sqlalchemy import event

from config.settings import settings

logger = logging.getLogger("world_eldoria.performance")


class UpdateTimingMiddleware(BaseMiddleware):
    """Log only slow Telegram updates; never log message text or user payloads."""

    async def __call__(self, handler, event_obj, data):
        started = time.perf_counter()
        try:
            return await handler(event_obj, data)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            if elapsed_ms >= settings.slow_update_ms:
                update_id = getattr(event_obj, "update_id", None)
                logger.warning(
                    "Slow Telegram update: update_id=%s duration_ms=%.1f event_type=%s",
                    update_id,
                    elapsed_ms,
                    type(event_obj).__name__,
                )


def install_slow_query_logging(engine) -> None:
    """Attach lightweight SQL timing hooks to an async SQLAlchemy engine."""

    sync_engine = engine.sync_engine

    @event.listens_for(sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        stack = conn.info.setdefault("_eldoria_query_started_at", [])
        stack.append(time.perf_counter())

    @event.listens_for(sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        stack = conn.info.get("_eldoria_query_started_at")
        if not stack:
            return
        started = stack.pop()
        elapsed_ms = (time.perf_counter() - started) * 1000
        if elapsed_ms >= settings.slow_db_query_ms:
            # Deliberately omit SQL and parameters to avoid leaking user/game data.
            logger.warning(
                "Slow database query: duration_ms=%.1f executemany=%s",
                elapsed_ms,
                bool(executemany),
            )

    @event.listens_for(sync_engine, "handle_error")
    def handle_error(exception_context):
        logger.error(
            "Database statement failed: connection_invalidated=%s exception_type=%s",
            bool(exception_context.is_disconnect),
            type(exception_context.original_exception).__name__
            if exception_context.original_exception is not None
            else "unknown",
        )
