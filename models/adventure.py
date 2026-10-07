from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class AdventureArea(Base):
    __tablename__ = "adventure_areas"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recommended_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    min_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    max_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    xp_reward: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    gold_reward: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


class AdventureEnemy(Base):
    __tablename__ = "adventure_enemies"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    area_id: Mapped[int] = mapped_column(
        ForeignKey(
            "adventure_areas.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # اتصال دشمن ماجراجویی به Monster
    monster_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "monsters.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # اطلاعات فعلی دشمن برای حفظ سازگاری
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    hp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )

    attack: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    defense: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    xp_reward: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    skill_xp_reward: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    gold_reward: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )