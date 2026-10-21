from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

PANEL_IMAGES_DIR = BASE_DIR / "assets" / "menu"
DUNGEON_IMAGES_DIR = BASE_DIR / "assets" / "dungeons"


PANEL_IMAGES = {
    "main_menu": PANEL_IMAGES_DIR / "main_menu.jpg",
    "inventory": PANEL_IMAGES_DIR / "inventory.jpg",
    "skills": PANEL_IMAGES_DIR / "skills.jpg",
    "equipment": PANEL_IMAGES_DIR / "equipment.jpg",
    "adventure": PANEL_IMAGES_DIR / "adventure.jpg",
    "quest": PANEL_IMAGES_DIR / "quest.jpg",
    "shop": PANEL_IMAGES_DIR / "shop.jpg",
    "fan_art": PANEL_IMAGES_DIR / "fan_art.jpg",
    "pvp": PANEL_IMAGES_DIR / "pvp.jpg",
    "settings": PANEL_IMAGES_DIR / "settings.jpg",

    # Dungeon panels
    "dungeon_eldoria_ruins": (
        DUNGEON_IMAGES_DIR / "eldoria_ruins.jpg"
    ),
    "dungeon_forgotten_crypt": (
        DUNGEON_IMAGES_DIR / "forgotten_crypt.jpg"
    ),
    "dungeon_eternal_flame_fortress": (
        DUNGEON_IMAGES_DIR / "eternal_flame_fortress.jpg"
    ),
    "dungeon_frozen_temple": (
        DUNGEON_IMAGES_DIR / "frozen_temple.jpg"
    ),
    "dungeon_shadow_abyss": (
        DUNGEON_IMAGES_DIR / "shadow_abyss.jpg"
    ),
    "dungeon_ancient_dragon_realm": (
        DUNGEON_IMAGES_DIR / "ancient_dragon_realm.jpg"
    ),
}