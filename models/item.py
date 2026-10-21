from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class Item(Base):
    __tablename__ = "items"

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

    item_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    rarity: Mapped[str] = mapped_column(
        String(32),
        default="common",
        nullable=False,
        index=True,
    )

    # Price used when the item is sold back to the shop.
    sell_price: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Price used when the item is bought from the shop.
    # 0 means the item is not sold by the shop.
    buy_price: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    is_tradeable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
