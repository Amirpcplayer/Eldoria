from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PANEL_IMAGES_DIR = BASE_DIR / "assets" / "menu"
DUNGEON_IMAGES_DIR = BASE_DIR / "assets" / "dungeons"

# Navigation panels are text-only so Telegram can edit the same message.
# Boss and fan-art media are sent by their dedicated handlers.
PANEL_IMAGES = {
    "profile": PANEL_IMAGES_DIR / "profile.jpg",
}
