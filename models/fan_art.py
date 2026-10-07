from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class FanArt(Base):
    __tablename__ = "fan_arts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    image_file_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    rarity: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_limited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    stock: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    orders: Mapped[list["FanArtOrder"]] = relationship(
        "FanArtOrder",
        back_populates="fan_art",
        cascade="all, delete-orphan",
    )

    ownerships: Mapped[list["FanArtOwnership"]] = relationship(
        "FanArtOwnership",
        back_populates="fan_art",
        cascade="all, delete-orphan",
    )


class FanArtOrder(Base):
    __tablename__ = "fan_art_orders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_code: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
        index=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    fan_art_id: Mapped[int] = mapped_column(
        ForeignKey("fan_arts.id"),
        nullable=False,
    )

    price_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    receipt_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    fan_art: Mapped["FanArt"] = relationship(
        "FanArt",
        back_populates="orders",
    )


class FanArtOwnership(Base):
    __tablename__ = "fan_art_ownerships"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    fan_art_id: Mapped[int] = mapped_column(
        ForeignKey("fan_arts.id"),
        nullable=False,
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("fan_art_orders.id"),
        nullable=True,
    )

    acquired_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    fan_art: Mapped["FanArt"] = relationship(
        "FanArt",
        back_populates="ownerships",
    )