"""Shared, safe visual language for World Eldoria text panels."""
from __future__ import annotations
import re

_TITLE_RE = re.compile(r"^\s*(?:🩸\s*)?(<b>[^\n]+?</b>|[^\n]{1,70})\s*$")

def style_panel(text: str | None) -> str | None:
    if not text or not text.strip():
        return text
    # Avoid repeated decoration if a panel is edited/re-rendered.
    if "╔══ اِلدوریا ══╗" in text:
        return text
    lines = text.splitlines()
    first = lines[0].strip() if lines else ""
    # Keep title untouched (including HTML) and frame it with a compact fantasy rule.
    if first and not first.startswith("🩸 ━"):
        lines[0] = f"🩸 <b>╔══ اِلدوریا ══╗</b>\n{first}\n<code>━━━━━━━━━━━━━━━━</code>"
    return "\n".join(lines)
