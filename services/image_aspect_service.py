from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.types import BufferedInputFile
from PIL import Image


async def prepare_photo(bot: Bot, source: Any, filename: str = "eldoria-image.jpg", portrait: bool = False) -> BufferedInputFile:
    """Return original image bytes without resizing, padding, cropping or re-encoding.

    The portrait argument remains for compatibility with existing callers.
    Telegram controls the in-chat photo preview and may compress sent photos.
    """
    raw = BytesIO()

    if isinstance(source, (str, Path)) and Path(str(source)).is_file():
        path = Path(str(source))
        raw.write(path.read_bytes())
    elif isinstance(source, (str, Path)):
        telegram_file = await bot.get_file(str(source))
        if not telegram_file.file_path:
            raise ValueError("Telegram did not return a downloadable image path.")
        await bot.download_file(telegram_file.file_path, destination=raw)
    else:
        raise TypeError(f"Unsupported image source: {type(source).__name__}")

    original = raw.getvalue()
    # Match the upload filename extension to the actual file format; never
    # change the image data just to fit a requested filename.
    with Image.open(BytesIO(original)) as image:
        extension = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(image.format)
    if extension:
        filename = str(Path(filename).with_suffix(extension))
    return BufferedInputFile(original, filename=filename)
