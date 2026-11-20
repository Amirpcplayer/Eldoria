"""Keep original artwork dimensions for Telegram photo previews.

Telegram receives the original image instead of a square canvas with blurred
padding. The source file is never modified.
"""
from pathlib import Path


def prepare_telegram_image(image_path: str | Path) -> Path:
    """Return the original image path without cropping, padding, or recompressing."""
    return Path(image_path)
