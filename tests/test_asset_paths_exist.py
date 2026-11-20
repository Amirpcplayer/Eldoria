from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_literal_asset_paths_in_python_sources_exist():
    missing: list[str] = []
    for source in ROOT.rglob("*.py"):
        if any(part in {".git", ".venv", "venv", "__pycache__"} for part in source.parts):
            continue
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue  # Syntax is covered by compileall; do not mask it here.
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value
                if value.startswith("assets/") and Path(value).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"} and not any(c in value for c in "{}*"):
                    if not (ROOT / value).is_file():
                        missing.append(f"{source.relative_to(ROOT)} -> {value}")
    assert not missing, "Missing referenced assets:\n" + "\n".join(sorted(set(missing)))
