from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class Monster(Base):
    __tablename__ = "monsters"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # =========================================================
    # BASIC IDENTITY
    # =========================================================

    # مثال:
    # wolf
    # goblin
    # orc
    family: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    # مثال:
    # normal_wolf
    # ice_wolf
    # fire_wolf
    # storm_wolf
    variant: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # =========================================================
    # POWER / TIER
    # =========================================================

    # normal
    # elite
    # boss
    # world_boss
    tier: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="normal",
        index=True,
    )

    # ضریب قدرت این Variant نسبت به موجود پایه
    # مثال:
    # 1.00 = معمولی
    # 1.10 = کمی قوی‌تر
    # 1.50 = Elite
    power_multiplier: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )

    # =========================================================
    # ELEMENT
    # =========================================================

    # neutral
    # fire
    # water
    # ice
    # earth
    # wind
    # electro
    # shadow
    # light
    # blood
    # steel
    element: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="neutral",
        index=True,
    )

    # =========================================================
    # BASE STAT PROFILE
    # =========================================================

    # این اعداد هنوز Stats نهایی هیولا نیستند.
    # در مراحل بعدی با Level و power_multiplier
    # تبدیل به Stats واقعی می‌شوند.

    base_hp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    base_attack: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    base_magic_power: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    base_defense: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    base_magic_defense: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    base_speed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    base_accuracy: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    base_luck: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    base_critical: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    # =========================================================
    # RESISTANCE
    # =========================================================

    # مثال:
    # fire_resistance = 0.25
    # یعنی 25٪ کاهش آسیب Fire
    fire_resistance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    water_resistance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    ice_resistance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    earth_resistance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    wind_resistance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    electro_resistance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    shadow_resistance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    light_resistance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    blood_resistance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    steel_resistance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    # =========================================================
    # STATUS
    # =========================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )