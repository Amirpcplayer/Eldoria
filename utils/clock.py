"""UTC clock helpers for the project's timestamp conventions.

Database ``DateTime`` columns in this project store naive UTC values, so use
``utcnow_naive`` for those columns and datetime comparisons. Use ``utcnow_aware``
when converting to Unix timestamps; naive ``datetime.timestamp()`` depends on
the host's local timezone.
"""
from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """Return the current UTC instant as a naive datetime for legacy DB columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utcnow_aware() -> datetime:
    """Return the current UTC instant as a timezone-aware datetime."""
    return datetime.now(timezone.utc)
