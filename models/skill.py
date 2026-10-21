from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    element: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    skill_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    rarity: Mapped[str] = mapped_column(
        String(32),
        default="common",
        nullable=False,
        index=True,
    )

    max_level: Mapped[int] = mapped_column(
        Integer,
        default=200,
        nullable=False,
    )

    base_power: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )

    power_per_level: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )

    mana_cost: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )

    cooldown: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )

    unlock_level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )