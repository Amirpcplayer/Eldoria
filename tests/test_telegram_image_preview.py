from pathlib import Path

from PIL import Image

from utils.telegram_image_preview import prepare_telegram_image


def test_portrait_preview_uses_original_file_without_modification(tmp_path: Path):
    source = tmp_path / "portrait.jpg"
    Image.new("RGB", (600, 1000), (220, 40, 40)).save(source)
    original_bytes = source.read_bytes()

    preview = prepare_telegram_image(source)

    assert preview == source
    assert source.read_bytes() == original_bytes
    with Image.open(preview) as rendered:
        assert rendered.size == (600, 1000)


def test_square_image_uses_original_file(tmp_path: Path):
    source = tmp_path / "square.jpg"
    Image.new("RGB", (800, 800), (20, 40, 60)).save(source)

    assert prepare_telegram_image(source) == source


def test_missing_image_path_is_returned_without_crashing(tmp_path: Path):
    source = tmp_path / "missing.jpg"

    assert prepare_telegram_image(source) == source
