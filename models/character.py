from datetime import datetime

from sqlalchemy import String, Integer, BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Telegram user IDs can exceed PostgreSQL INTEGER (INT4) range.
    # BIGINT is required for modern Telegram IDs.
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )

    race: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # XP مخصوص Level قهرمان
    xp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # XP جداگانه برای ارتقای مهارت‌ها
    skill_xp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    gold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    gems: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    hp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    max_hp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    mana: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    max_mana: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    attack: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    magic_power: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    defense: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    magic_defense: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    speed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    accuracy: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    luck: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    critical: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )