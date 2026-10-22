from __future__ import annotations

import re
import unicodedata


def name_key(value: str) -> str:
    """Canonical comparison key for Persian/Arabic and Latin group names."""
    value = unicodedata.normalize("NFKC", value or "").casefold()
    value = value.translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه", "أ": "ا", "إ": "ا", "ٱ": "ا"}))
    value = "".join(ch for ch in value if unicodedata.category(ch) not in {"Cf", "Mn", "Me"})
    return re.sub(r"\s+", "", value)


async def reserve_name_check(session, lock_id: int, model, candidate: str, *, active_only: bool = False, exclude_id: int | None = None) -> bool:
    """Serialize name mutations within each group type to prevent concurrent duplicates."""
    from sqlalchemy import select, text
    await session.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
    stmt = select(model.id, model.name)
    if active_only:
        stmt = stmt.where(model.status == "open")
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)
    rows = (await session.execute(stmt)).all()
    key = name_key(candidate)
    return any(name_key(existing) == key for _, existing in rows)
