from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class Quest(Base):
    __tablename__ = "quests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="story",
    )

    objective_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    target_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    required_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    min_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    prerequisite_quest_id: Mapped[int | None] = mapped_column(
        ForeignKey("quests.id"),
        nullable=True,
    )

    reward_xp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    reward_skill_xp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    reward_gold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    reward_equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipments.id"),
        nullable=True,
    )

    is_repeatable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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


class CharacterQuest(Base):
    __tablename__ = "character_quests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id"),
        nullable=False,
        index=True,
    )

    quest_id: Mapped[int] = mapped_column(
        ForeignKey("quests.id"),
        nullable=False,
        index=True,
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "character_id",
            "quest_id",
            name="uq_character_quests_character_quest",
        ),
    )