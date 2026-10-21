from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class Equipment(Base):
    __tablename__ = "equipments"

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

    # گروه ست برای پاداش چندقطعه‌ای؛ NULL یعنی تجهیز بدون ست.
    set_key: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )

    # weapon / helmet / armor / boots / ring / necklace
    equipment_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    # common / uncommon / rare / epic / legendary / mythic / divine
    rarity: Mapped[str] = mapped_column(
        String(32),
        default="common",
        nullable=False,
        index=True,
    )

    required_level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    shop_price: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    gem_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    attack: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    magic_power: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    defense: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    magic_defense: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    hp: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    mana: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    speed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    accuracy: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    critical: Mapped[int] = mapped_column(
        Integer,
        default=0,
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


class CharacterEquipment(Base):
    __tablename__ = "character_equipments"

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

    equipment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "equipments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    equipped: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    enhancement_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_character_equipment_character_equipped",
            "character_id",
            "equipped",
        ),
    )