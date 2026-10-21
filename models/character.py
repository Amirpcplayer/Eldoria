# models/character.py

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base
from models.fan_art import FanArt  # noqa: F401


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )

    telegram_username: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
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

    gender: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="male",
        server_default="male",
    )

    level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    xp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    skill_xp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    crafting_xp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    active_title: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default="شاگرد اِلدوریا",
    )

    unlocked_titles: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
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

    dead_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    last_vitals_recovery_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=datetime.utcnow
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

    active_fan_art_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("fan_arts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )