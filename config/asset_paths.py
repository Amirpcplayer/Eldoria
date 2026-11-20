from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# همهٔ تصاویر رابط کاربری با پسوند JPG نگه‌داری می‌شوند.
ASSET_PATHS = {
    "boss": ASSETS_DIR / "bosses",
    "dungeon": ASSETS_DIR / "dungeons",
    "adventure": ASSETS_DIR / "adventure",
    "menu": ASSETS_DIR / "menu",
    "characters": ASSETS_DIR / "characters",
    "monsters": ASSETS_DIR / "monsters",
    "skills": ASSETS_DIR / "skills",
    "combat": ASSETS_DIR / "combat",
    "quests": ASSETS_DIR / "quests",
    "party": ASSETS_DIR / "party",
    "guild": ASSETS_DIR / "guild",
    "pvp": ASSETS_DIR / "pvp",
    "ranking": ASSETS_DIR / "ranking",
    "shop": ASSETS_DIR / "shop",
    "fan_art": ASSETS_DIR / "fan_art",
    "settings": ASSETS_DIR / "settings",
    "admin": ASSETS_DIR / "admin",
    "ui": ASSETS_DIR / "ui",
}

def image_path(section: str, filename: str) -> Path:
    if not filename.lower().endswith(".jpg"):
        raise ValueError("Only .jpg images are supported")
    if section not in ASSET_PATHS:
        raise KeyError(f"Unknown asset section: {section}")
    return ASSET_PATHS[section] / filename
