"""Shared, safe visual language for World Eldoria text panels."""
from __future__ import annotations

_FRAME = "╔══ اِلدوریا ══╗"

def style_panel(text: str | None) -> str | None:
    if not text or not text.strip():
        return text
    # Avoid repeated decoration if a panel is edited/re-rendered.
    if text.lstrip().startswith(f"🩸 <b>{_FRAME}</b>"):
        return text
    lines = text.splitlines(keepends=True)
    title_index = next(i for i, line in enumerate(lines) if line.strip())
    first = lines[title_index].strip()
    # Do not strip body whitespace or trailing newlines on each render.
    if first.startswith("🩸 ━"):
        return text
    ending = "\n" if lines[title_index].endswith(("\n", "\r")) else ""
    lines[title_index] = (
        f"🩸 <b>{_FRAME}</b>\n{first}\n"
        f"<code>━━━━━━━━━━━━━━━━</code>{ending}"
    )
    return "".join(lines)
