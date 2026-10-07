from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class CharacterSkill(Base):
    __tablename__ = "character_skills"

    __table_args__ = (
        UniqueConstraint(
            "character_id",
            "skill_id",
            name="uq_character_skill",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    character_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "characters.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    skill_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "skills.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    slot: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    unlocked: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )