from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonsterVariant:
    key: str
    name: str
    description: str
    tier: str
    element: str
    power_multiplier: float

    base_hp: int
    base_attack: int
    base_magic_power: int
    base_defense: int
    base_magic_defense: int
    base_speed: int
    base_accuracy: int
    base_luck: int
    base_critical: int

    resistances: dict[str, float]


# ============================================================
# WOLF
# ============================================================

WOLF_VARIANTS = [
    MonsterVariant(
        key="normal_wolf",
        name="گرگ معمولی",
        description="گرگی وحشی و سریع که در جنگل‌های اِلدوریا پرسه می‌زند.",
        tier="normal",
        element="neutral",
        power_multiplier=1.00,
        base_hp=100,
        base_attack=12,
        base_magic_power=5,
        base_defense=8,
        base_magic_defense=6,
        base_speed=12,
        base_accuracy=10,
        base_luck=5,
        base_critical=5,
        resistances={},
    ),
    MonsterVariant(
        key="ice_wolf",
        name="گرگ یخی",
        description="گرگی که نیروی سرمای شدید را در بدن خود دارد.",
        tier="normal",
        element="ice",
        power_multiplier=1.08,
        base_hp=115,
        base_attack=11,
        base_magic_power=8,
        base_defense=10,
        base_magic_defense=12,
        base_speed=10,
        base_accuracy=10,
        base_luck=5,
        base_critical=5,
        resistances={
            "ice": 0.40,
            "fire": -0.25,
        },
    ),
    MonsterVariant(
        key="fire_wolf",
        name="گرگ آتشین",
        description="گرگی خشمگین که بدنش با شعله‌های آتش پوشیده شده است.",
        tier="normal",
        element="fire",
        power_multiplier=1.08,
        base_hp=105,
        base_attack=15,
        base_magic_power=10,
        base_defense=7,
        base_magic_defense=8,
        base_speed=12,
        base_accuracy=10,
        base_luck=5,
        base_critical=8,
        resistances={
            "fire": 0.40,
            "ice": -0.25,
        },
    ),
    MonsterVariant(
        key="water_wolf",
        name="گرگ آبی",
        description="گرگی سازگار با آب که در مناطق مرطوب زندگی می‌کند.",
        tier="normal",
        element="water",
        power_multiplier=1.08,
        base_hp=125,
        base_attack=10,
        base_magic_power=10,
        base_defense=10,
        base_magic_defense=10,
        base_speed=9,
        base_accuracy=10,
        base_luck=6,
        base_critical=5,
        resistances={
            "water": 0.40,
            "electro": -0.25,
        },
    ),
    MonsterVariant(
        key="storm_wolf",
        name="گرگ طوفانی",
        description="گرگی بسیار سریع که نیروی صاعقه در وجودش جریان دارد.",
        tier="elite",
        element="electro",
        power_multiplier=1.25,
        base_hp=120,
        base_attack=16,
        base_magic_power=14,
        base_defense=8,
        base_magic_defense=10,
        base_speed=18,
        base_accuracy=13,
        base_luck=8,
        base_critical=10,
        resistances={
            "electro": 0.45,
            "water": 0.20,
        },
    ),
    MonsterVariant(
        key="shadow_wolf",
        name="گرگ سایه",
        description="شکارچی مرموزی که در تاریکی حرکت می‌کند.",
        tier="elite",
        element="shadow",
        power_multiplier=1.28,
        base_hp=110,
        base_attack=18,
        base_magic_power=15,
        base_defense=7,
        base_magic_defense=13,
        base_speed=17,
        base_accuracy=14,
        base_luck=12,
        base_critical=15,
        resistances={
            "shadow": 0.45,
            "light": -0.30,
        },
    ),
    MonsterVariant(
        key="blood_wolf",
        name="گرگ خونین",
        description="گرگی وحشی که با نیروی خون دشمنانش قدرتمندتر می‌شود.",
        tier="elite",
        element="blood",
        power_multiplier=1.30,
        base_hp=145,
        base_attack=19,
        base_magic_power=8,
        base_defense=10,
        base_magic_defense=8,
        base_speed=13,
        base_accuracy=11,
        base_luck=8,
        base_critical=10,
        resistances={
            "blood": 0.45,
        },
    ),
    MonsterVariant(
        key="steel_wolf",
        name="گرگ فولادی",
        description="گرگی با پوستی سخت و مقاوم مانند فولاد.",
        tier="elite",
        element="steel",
        power_multiplier=1.30,
        base_hp=175,
        base_attack=14,
        base_magic_power=4,
        base_defense=20,
        base_magic_defense=14,
        base_speed=7,
        base_accuracy=9,
        base_luck=4,
        base_critical=5,
        resistances={
            "steel": 0.50,
            "fire": -0.20,
        },
    ),
    MonsterVariant(
        key="alpha_wolf",
        name="آلفای گرگ‌ها",
        description="رهبر قدرتمند گله که سایر گرگ‌ها از او فرمان می‌برند.",
        tier="boss",
        element="neutral",
        power_multiplier=1.70,
        base_hp=220,
        base_attack=25,
        base_magic_power=10,
        base_defense=16,
        base_magic_defense=12,
        base_speed=16,
        base_accuracy=14,
        base_luck=10,
        base_critical=12,
        resistances={},
    ),
    MonsterVariant(
        key="fenrir",
        name="Fenrir",
        description="گرگ افسانه‌ای که قدرتی فراتر از موجودات معمولی دارد.",
        tier="world_boss",
        element="shadow",
        power_multiplier=3.00,
        base_hp=500,
        base_attack=45,
        base_magic_power=30,
        base_defense=30,
        base_magic_defense=25,
        base_speed=22,
        base_accuracy=18,
        base_luck=15,
        base_critical=20,
        resistances={
            "shadow": 0.70,
            "light": -0.25,
            "fire": 0.20,
            "ice": 0.20,
            "water": 0.20,
            "electro": 0.20,
        },
    ),
]


# ============================================================
# GOBLIN
# ============================================================

GOBLIN_VARIANTS = [
    MonsterVariant(
        key="goblin",
        name="گابلین",
        description="موجودی کوچک اما مهاجم که معمولاً به صورت گروهی شکار می‌کند.",
        tier="normal",
        element="neutral",
        power_multiplier=1.00,
        base_hp=110,
        base_attack=14,
        base_magic_power=4,
        base_defense=8,
        base_magic_defense=5,
        base_speed=11,
        base_accuracy=9,
        base_luck=7,
        base_critical=5,
        resistances={},
    ),
    MonsterVariant(
        key="fire_goblin",
        name="گابلین آتشین",
        description="گابلینی که از جادوی ابتدایی آتش استفاده می‌کند.",
        tier="normal",
        element="fire",
        power_multiplier=1.08,
        base_hp=105,
        base_attack=15,
        base_magic_power=10,
        base_defense=7,
        base_magic_defense=8,
        base_speed=11,
        base_accuracy=10,
        base_luck=6,
        base_critical=6,
        resistances={
            "fire": 0.35,
            "ice": -0.20,
        },
    ),
    MonsterVariant(
        key="ice_goblin",
        name="گابلین یخی",
        description="گابلینی که از جادوی سرمای ضعیف استفاده می‌کند.",
        tier="normal",
        element="ice",
        power_multiplier=1.08,
        base_hp=115,
        base_attack=12,
        base_magic_power=11,
        base_defense=8,
        base_magic_defense=10,
        base_speed=9,
        base_accuracy=10,
        base_luck=6,
        base_critical=5,
        resistances={
            "ice": 0.35,
            "fire": -0.20,
        },
    ),
    MonsterVariant(
        key="goblin_archer",
        name="کماندار گابلین",
        description="گابلینی سریع که از فاصله دور حمله می‌کند.",
        tier="normal",
        element="neutral",
        power_multiplier=1.10,
        base_hp=100,
        base_attack=17,
        base_magic_power=3,
        base_defense=6,
        base_magic_defense=5,
        base_speed=14,
        base_accuracy=15,
        base_luck=8,
        base_critical=8,
        resistances={},
    ),
    MonsterVariant(
        key="goblin_warrior",
        name="جنگجوی گابلین",
        description="گابلینی آموزش‌دیده که تجهیزات جنگی بهتری دارد.",
        tier="elite",
        element="neutral",
        power_multiplier=1.25,
        base_hp=150,
        base_attack=21,
        base_magic_power=3,
        base_defense=13,
        base_magic_defense=8,
        base_speed=10,
        base_accuracy=11,
        base_luck=6,
        base_critical=7,
        resistances={},
    ),
    MonsterVariant(
        key="goblin_shaman",
        name="شمن گابلین",
        description="گابلینی جادوگر که از جادوی ابتدایی استفاده می‌کند.",
        tier="elite",
        element="earth",
        power_multiplier=1.28,
        base_hp=125,
        base_attack=10,
        base_magic_power=24,
        base_defense=7,
        base_magic_defense=15,
        base_speed=9,
        base_accuracy=13,
        base_luck=10,
        base_critical=8,
        resistances={
            "earth": 0.40,
        },
    ),
    MonsterVariant(
        key="goblin_elite",
        name="گابلین نخبه",
        description="یکی از قدرتمندترین جنگجویان قبیله گابلین.",
        tier="elite",
        element="neutral",
        power_multiplier=1.45,
        base_hp=190,
        base_attack=26,
        base_magic_power=5,
        base_defense=16,
        base_magic_defense=10,
        base_speed=12,
        base_accuracy=13,
        base_luck=9,
        base_critical=10,
        resistances={},
    ),
    MonsterVariant(
        key="goblin_king",
        name="پادشاه گابلین",
        description="فرمانروای قبیله گابلین و دشمنی بسیار خطرناک.",
        tier="boss",
        element="shadow",
        power_multiplier=1.85,
        base_hp=280,
        base_attack=34,
        base_magic_power=18,
        base_defense=20,
        base_magic_defense=15,
        base_speed=12,
        base_accuracy=14,
        base_luck=12,
        base_critical=12,
        resistances={
            "shadow": 0.25,
        },
    ),
]


# ============================================================
# BANDIT
# ============================================================

BANDIT_VARIANTS = [
    MonsterVariant(
        key="forest_bandit",
        name="راهزن جنگل",
        description="راهزنی که در مسیرهای جنگلی به مسافران حمله می‌کند.",
        tier="normal",
        element="neutral",
        power_multiplier=1.10,
        base_hp=140,
        base_attack=18,
        base_magic_power=3,
        base_defense=10,
        base_magic_defense=6,
        base_speed=13,
        base_accuracy=13,
        base_luck=8,
        base_critical=8,
        resistances={},
    ),
]


# ============================================================
# GOLEM
# ============================================================

GOLEM_VARIANTS = [
    MonsterVariant(
        key="stone_golem",
        name="گولم سنگی",
        description="موجودی عظیم ساخته‌شده از سنگ‌های کوهستان.",
        tier="elite",
        element="earth",
        power_multiplier=1.40,
        base_hp=300,
        base_attack=28,
        base_magic_power=5,
        base_defense=28,
        base_magic_defense=16,
        base_speed=5,
        base_accuracy=8,
        base_luck=3,
        base_critical=4,
        resistances={
            "earth": 0.55,
            "steel": 0.25,
            "wind": -0.20,
        },
    ),
    MonsterVariant(
        key="fire_golem",
        name="گولم آتشین",
        description="گولمی ساخته‌شده از سنگ و آتش که در سرزمین‌های آتشفشانی زندگی می‌کند.",
        tier="elite",
        element="fire",
        power_multiplier=1.65,
        base_hp=420,
        base_attack=36,
        base_magic_power=20,
        base_defense=32,
        base_magic_defense=20,
        base_speed=6,
        base_accuracy=9,
        base_luck=4,
        base_critical=5,
        resistances={
            "fire": 0.65,
            "earth": 0.30,
            "water": -0.30,
        },
    ),
]


# ============================================================
# BEAR
# ============================================================

BEAR_VARIANTS = [
    MonsterVariant(
        key="mountain_bear",
        name="خرس کوهستانی",
        description="خرسی عظیم و قدرتمند که در کوهستان زندگی می‌کند.",
        tier="elite",
        element="neutral",
        power_multiplier=1.45,
        base_hp=350,
        base_attack=35,
        base_magic_power=2,
        base_defense=20,
        base_magic_defense=10,
        base_speed=8,
        base_accuracy=10,
        base_luck=5,
        base_critical=6,
        resistances={},
    ),
]


# ============================================================
# SCORPION
# ============================================================

SCORPION_VARIANTS = [
    MonsterVariant(
        key="giant_scorpion",
        name="عقرب غول‌پیکر",
        description="عقربی عظیم که در شن‌های بیابان پنهان می‌شود.",
        tier="elite",
        element="earth",
        power_multiplier=1.60,
        base_hp=450,
        base_attack=42,
        base_magic_power=8,
        base_defense=24,
        base_magic_defense=14,
        base_speed=11,
        base_accuracy=12,
        base_luck=8,
        base_critical=8,
        resistances={
            "earth": 0.40,
            "water": -0.15,
        },
    ),
]


# ============================================================
# SERPENT
# ============================================================

SERPENT_VARIANTS = [
    MonsterVariant(
        key="sand_serpent",
        name="مار شنی",
        description="ماری عظیم که در زیر شن‌های بیابان حرکت می‌کند.",
        tier="elite",
        element="earth",
        power_multiplier=1.80,
        base_hp=520,
        base_attack=50,
        base_magic_power=8,
        base_defense=28,
        base_magic_defense=15,
        base_speed=13,
        base_accuracy=13,
        base_luck=7,
        base_critical=9,
        resistances={
            "earth": 0.45,
            "wind": -0.20,
        },
    ),
]


# ============================================================
# DRAKE
# ============================================================

DRAKE_VARIANTS = [
    MonsterVariant(
        key="fire_drake",
        name="دریک آتشین",
        description="اژدهایی کوچک اما بسیار خطرناک که از آتش استفاده می‌کند.",
        tier="boss",
        element="fire",
        power_multiplier=2.10,
        base_hp=650,
        base_attack=62,
        base_magic_power=35,
        base_defense=35,
        base_magic_defense=25,
        base_speed=14,
        base_accuracy=14,
        base_luck=10,
        base_critical=12,
        resistances={
            "fire": 0.65,
            "ice": -0.30,
            "water": -0.20,
        },
    ),
]


# ============================================================
# DARK SPIRIT
# ============================================================

DARK_SPIRIT_VARIANTS = [
    MonsterVariant(
        key="dark_spirit",
        name="روح تاریک",
        description="روحی قدرتمند که از اعماق تاریکی برخاسته است.",
        tier="elite",
        element="shadow",
        power_multiplier=2.00,
        base_hp=700,
        base_attack=35,
        base_magic_power=60,
        base_defense=18,
        base_magic_defense=35,
        base_speed=15,
        base_accuracy=15,
        base_luck=12,
        base_critical=12,
        resistances={
            "shadow": 0.60,
            "light": -0.35,
        },
    ),
]


# ============================================================
# SHADOW DEMON
# ============================================================

SHADOW_DEMON_VARIANTS = [
    MonsterVariant(
        key="shadow_demon",
        name="شیطان سایه",
        description="موجودی اهریمنی که از نیروی سایه تغذیه می‌کند.",
        tier="boss",
        element="shadow",
        power_multiplier=2.35,
        base_hp=900,
        base_attack=55,
        base_magic_power=75,
        base_defense=28,
        base_magic_defense=45,
        base_speed=16,
        base_accuracy=16,
        base_luck=14,
        base_critical=15,
        resistances={
            "shadow": 0.70,
            "light": -0.40,
            "blood": 0.20,
        },
    ),
]


# ============================================================
# LEGENDARY CREATURE
# ============================================================

LEGENDARY_CREATURE_VARIANTS = [
    MonsterVariant(
        key="legendary_creature",
        name="موجود افسانه‌ای",
        description="موجودی کمیاب با قدرتی ناشناخته و عظیم.",
        tier="boss",
        element="light",
        power_multiplier=2.60,
        base_hp=1200,
        base_attack=75,
        base_magic_power=80,
        base_defense=40,
        base_magic_defense=45,
        base_speed=18,
        base_accuracy=17,
        base_luck=18,
        base_critical=16,
        resistances={
            "light": 0.60,
            "shadow": -0.30,
            "fire": 0.20,
            "ice": 0.20,
            "water": 0.20,
            "electro": 0.20,
        },
    ),
]


# ============================================================
# ANCIENT DRAGON
# ============================================================

ANCIENT_DRAGON_VARIANTS = [
    MonsterVariant(
        key="ancient_dragon",
        name="اژدهای باستانی",
        description="یکی از قدرتمندترین موجودات شناخته‌شده در اِلدوریا.",
        tier="world_boss",
        element="fire",
        power_multiplier=3.20,
        base_hp=2000,
        base_attack=110,
        base_magic_power=100,
        base_defense=65,
        base_magic_defense=60,
        base_speed=20,
        base_accuracy=18,
        base_luck=20,
        base_critical=20,
        resistances={
            "fire": 0.75,
            "ice": 0.20,
            "water": -0.25,
            "earth": 0.40,
            "wind": 0.30,
            "electro": 0.30,
            "shadow": 0.20,
            "light": 0.20,
        },
    ),
]


# ============================================================
# ALL MONSTER FAMILIES
# ============================================================

MONSTER_FAMILIES: dict[str, list[MonsterVariant]] = {
    "wolf": WOLF_VARIANTS,
    "goblin": GOBLIN_VARIANTS,
    "bandit": BANDIT_VARIANTS,
    "golem": GOLEM_VARIANTS,
    "bear": BEAR_VARIANTS,
    "scorpion": SCORPION_VARIANTS,
    "serpent": SERPENT_VARIANTS,
    "drake": DRAKE_VARIANTS,
    "dark_spirit": DARK_SPIRIT_VARIANTS,
    "shadow_demon": SHADOW_DEMON_VARIANTS,
    "legendary_creature": LEGENDARY_CREATURE_VARIANTS,
    "ancient_dragon": ANCIENT_DRAGON_VARIANTS,
}


# ============================================================
# HELPERS
# ============================================================

def get_all_monster_variants() -> list[MonsterVariant]:
    variants: list[MonsterVariant] = []

    for family_variants in MONSTER_FAMILIES.values():
        variants.extend(family_variants)

    return variants


def get_monster_variant(
    variant_key: str,
) -> MonsterVariant | None:

    for variant in get_all_monster_variants():
        if variant.key == variant_key:
            return variant

    return None