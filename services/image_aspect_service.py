from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.types import BufferedInputFile
from PIL import Image, ImageOps

# A phone-wallpaper portrait frame for bot artwork. Images are contained, never
# stretched or cropped; other aspect ratios receive padding.
FRAME_SIZE = (1080, 1920)
FRAME_COLOR = (18, 20, 30)


async def prepare_photo(bot: Bot, source: Any, filename: str = "eldoria-image.jpg", portrait: bool = False) -> BufferedInputFile:
    """Normalize images to a phone-wallpaper portrait canvas without cropping."""
    raw = BytesIO()

    if isinstance(source, (str, Path)) and Path(str(source)).is_file():
        with Path(str(source)).open("rb") as file:
            raw.write(file.read())
    elif isinstance(source, (str, Path)):
        telegram_file = await bot.get_file(str(source))
        if not telegram_file.file_path:
            raise ValueError("Telegram did not return a downloadable image path.")
        await bot.download_file(telegram_file.file_path, destination=raw)
    else:
        raise TypeError(f"Unsupported image source: {type(source).__name__}")

    raw.seek(0)
    with Image.open(raw) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        frame_size = FRAME_SIZE
        image.thumbnail(frame_size, Image.Resampling.LANCZOS)

        frame = Image.new("RGB", frame_size, FRAME_COLOR)
        x = (frame_size[0] - image.width) // 2
        y = (frame_size[1] - image.height) // 2
        frame.paste(image, (x, y))

        output = BytesIO()
        frame.save(output, format="JPEG", quality=94, optimize=True)
        return BufferedInputFile(output.getvalue(), filename=filename)
