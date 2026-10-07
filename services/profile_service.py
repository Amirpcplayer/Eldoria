from models.character import Character
from services.xp_service import get_required_xp


RANKS = [
    ("SSS", 90),
    ("SS", 75),
    ("S", 60),
    ("A", 45),
    ("B", 30),
    ("C", 20),
    ("D", 10),
    ("F", 0),
]


TITLES = [
    (100, "👑 خدای جهان"),
    (90, "🌌 افسانه جاودان"),
    (80, "⚡ نیمه‌خدا"),
    (70, "🔥 فاتح ابدی"),
    (60, "🌠 ارباب اسطوره‌ای"),
    (50, "🏰 فرمانده اعظم"),
    (40, "👑 قهرمان افسانه‌ای"),
    (30, "⚔️ جنگجوی نخبه"),
    (20, "🔮 جادوگر"),
    (10, "🛡️ شوالیه"),
    (1, "⚔️ سرباز"),
]


def get_rank(level: int) -> str:
    for rank, minimum_level in RANKS:
        if level >= minimum_level:
            return rank

    return "F"


def get_title(level: int) -> str:
    for minimum_level, title in TITLES:
        if level >= minimum_level:
            return title

    return "⚔️ سرباز"


def get_xp_progress(
    level: int,
    xp: int,
) -> tuple[int, int, int]:

    if level >= 100:
        return 0, 0, 100

    required = get_required_xp(level)

    if required <= 0:
        return 0, 0, 100

    current = max(xp, 0)

    # اینجا دیگر XP از سقف موردنیاز عبور نمی‌کند،
    # چون xp_service مقدار اضافه را به Level بعد منتقل می‌کند.
    current = min(current, required)

    percentage = int(
        (current / required) * 100
    )

    return current, required, percentage


def create_xp_bar(
    percentage: int,
    length: int = 10,
) -> str:

    percentage = max(
        0,
        min(percentage, 100),
    )

    filled = round(
        length * percentage / 100
    )

    return (
        "🟩" * filled
        + "⬜" * (length - filled)
    )


def get_combat_power(
    character: Character,
) -> int:

    power = (
        character.hp * 1.0
        + character.max_hp * 0.5
        + character.mana * 0.5
        + character.max_mana * 0.3
        + character.attack * 8
        + character.magic_power * 8
        + character.defense * 6
        + character.magic_defense * 6
        + character.speed * 5
        + character.accuracy * 5
        + character.luck * 4
        + character.critical * 10
        + character.level * 25
    )

    return int(power)