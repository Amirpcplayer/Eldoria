from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# Ordinary player menus are text-only and are edited in-place.
# Profile images are dynamic and rendered by handlers/profile.py.
# Fan Art cards and boss artwork are sent by their dedicated handlers.
# Do not add ordinary menu images here, otherwise panel navigation will create
# a fresh photo message instead of editing the current panel.
PANEL_IMAGES: dict[str, Path] = {}
