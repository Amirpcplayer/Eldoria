"""Prepare local portrait artwork so Telegram chat previews show the full image.

Telegram clients can visually crop/tall-limit portrait photos in the chat timeline.
This helper places the entire original image on a square canvas with a blurred,
cover-fitted copy behind it. The source artwork is never cropped in the foreground.
"""
from __future__ import annotations

import hashlib
import logging
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger(__name__)
CANVAS_SIZE = 1024
PADDING = 28
_CACHE_DIR = Path(tempfile.gettempdir()) / "world_eldoria_image_previews"


def prepare_telegram_image(image_path: str | Path) -> Path:
    """Return a cached square JPEG preview for a local image, preserving all content.

    If Pillow cannot process the image, return the original path so image delivery
    remains available rather than breaking the bot's panel.
    """
    source = Path(image_path)
    try:
        if not source.is_file():
            return source
        source_stat = source.stat()
        cache_key = hashlib.sha256(
            f"v2:{CANVAS_SIZE}:{PADDING}:{source.resolve()}:"
            f"{source_stat.st_size}:{source_stat.st_mtime_ns}".encode()
        ).hexdigest()[:24]
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        output = _CACHE_DIR / f"{cache_key}.jpg"
        if output.is_file():
            return output

        with Image.open(source) as opened:
            # Do not silently turn animations into still images.
            if getattr(opened, "is_animated", False):
                return source
            rgba = ImageOps.exif_transpose(opened).convert("RGBA")
            matte = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            original = Image.alpha_composite(matte, rgba).convert("RGB")

        # Near-square images need no padding.
        ratio = original.width / original.height
        if 0.85 <= ratio <= 1.18:
            return source

        canvas_size = CANVAS_SIZE
        background = ImageOps.fit(
            original,
            (canvas_size, canvas_size),
            method=Image.Resampling.LANCZOS,
        ).filter(ImageFilter.GaussianBlur(radius=28))

        # Slight darkening makes the complete, un-cropped artwork stand out.
        overlay = Image.new("RGB", background.size, (0, 0, 0))
        background = Image.blend(background, overlay, 0.18)

        max_content = canvas_size - (PADDING * 2)
        foreground = ImageOps.contain(
            original,
            (max_content, max_content),
            method=Image.Resampling.LANCZOS,
        )
        x = (canvas_size - foreground.width) // 2
        y = (canvas_size - foreground.height) // 2
        background.paste(foreground, (x, y))
        # Publish only a complete JPEG; concurrent readers never see a partial file.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=_CACHE_DIR, suffix=".jpg", delete=False) as handle:
                temporary = Path(handle.name)
                background.save(handle, format="JPEG", quality=92, optimize=True)
            temporary.replace(output)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return output
    except Exception:
        logger.exception("Could not prepare Telegram image preview for %s", source)
        return source
