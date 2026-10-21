from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.database import AsyncSessionLocal
from models.character import Character
from models.fan_art import FanArt, FanArtOrder, FanArtOwnership


PENDING_PAYMENT = "PENDING_PAYMENT"
WAITING_RECEIPT = "WAITING_RECEIPT"
UNDER_REVIEW = "UNDER_REVIEW"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
CANCELLED = "CANCELLED"

ACTIVE_ORDER_STATUSES = (
    PENDING_PAYMENT,
    WAITING_RECEIPT,
    UNDER_REVIEW,
)


async def get_active_fan_arts() -> list[FanArt]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FanArt)
            .where(FanArt.is_active.is_(True))
            .order_by(FanArt.display_order.asc(), FanArt.id.asc())
        )
        return list(result.scalars().all())


async def get_fan_art(fan_art_id: int) -> FanArt | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(FanArt).where(FanArt.id == fan_art_id)
        )


async def owns_fan_art(telegram_id: int, fan_art_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FanArtOwnership.id)
            .where(
                FanArtOwnership.telegram_id == telegram_id,
                FanArtOwnership.fan_art_id == fan_art_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None


async def get_owned_fan_arts(telegram_id: int) -> list[FanArt]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FanArt)
            .join(FanArtOwnership, FanArtOwnership.fan_art_id == FanArt.id)
            .where(FanArtOwnership.telegram_id == telegram_id)
            .order_by(
                FanArtOwnership.acquired_at.desc(),
                FanArt.id.desc(),
            )
        )
        return list(result.scalars().all())


async def get_active_fan_art(telegram_id: int) -> FanArt | None:
    """Return the player's selected Fan Art only when they still own it."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FanArt)
            .join(
                FanArtOwnership,
                FanArtOwnership.fan_art_id == FanArt.id,
            )
            .join(
                Character,
                Character.active_fan_art_id == FanArt.id,
            )
            .where(
                Character.telegram_id == telegram_id,
                FanArtOwnership.telegram_id == telegram_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()


async def set_active_fan_art(
    telegram_id: int,
    fan_art_id: int,
) -> tuple[bool, str]:
    """Select an owned Fan Art as the player's active profile artwork."""
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == telegram_id)
        )
        if character is None:
            return False, "❌ قهرمان پیدا نشد."

        ownership = await session.scalar(
            select(FanArtOwnership.id)
            .where(
                FanArtOwnership.telegram_id == telegram_id,
                FanArtOwnership.fan_art_id == fan_art_id,
            )
            .limit(1)
        )
        if ownership is None:
            return False, "❌ این Fan Art متعلق به شما نیست."

        fan_art = await session.scalar(
            select(FanArt).where(FanArt.id == fan_art_id)
        )
        if fan_art is None:
            return False, "❌ Fan Art پیدا نشد."

        character.active_fan_art_id = fan_art_id
        await session.commit()

        return True, f"✅ Fan Art «{fan_art.name}» فعال شد."


async def clear_active_fan_art(telegram_id: int) -> tuple[bool, str]:
    """Remove the active Fan Art without affecting ownership."""
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == telegram_id)
        )
        if character is None:
            return False, "❌ قهرمان پیدا نشد."

        character.active_fan_art_id = None
        await session.commit()
        return True, "✅ Fan Art فعال حذف شد."


async def get_active_order(telegram_id: int) -> FanArtOrder | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .where(
                FanArtOrder.telegram_id == telegram_id,
                FanArtOrder.status.in_(ACTIVE_ORDER_STATUSES),
            )
            .order_by(FanArtOrder.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def create_order(telegram_id: int, fan_art_id: int) -> FanArtOrder:
    async with AsyncSessionLocal() as session:
        active_result = await session.execute(
            select(FanArtOrder)
            .where(
                FanArtOrder.telegram_id == telegram_id,
                FanArtOrder.status.in_(ACTIVE_ORDER_STATUSES),
            )
            .limit(1)
        )
        if active_result.scalar_one_or_none() is not None:
            raise ValueError("ACTIVE_ORDER_EXISTS")

        fan_art = await session.scalar(
            select(FanArt).where(
                FanArt.id == fan_art_id,
                FanArt.is_active.is_(True),
            )
        )
        if fan_art is None:
            raise ValueError("FAN_ART_NOT_FOUND")

        if fan_art.is_limited and (fan_art.stock is None or fan_art.stock <= 0):
            raise ValueError("OUT_OF_STOCK")

        ownership = await session.scalar(
            select(FanArtOwnership.id)
            .where(
                FanArtOwnership.telegram_id == telegram_id,
                FanArtOwnership.fan_art_id == fan_art_id,
            )
            .limit(1)
        )
        if ownership is not None:
            raise ValueError("ALREADY_OWNED")

        timestamp = datetime.utcnow()
        order_code = (
            f"ELD-{timestamp:%Y%m%d}-"
            f"{int(timestamp.timestamp() * 1000) % 100000:05d}"
        )

        order = FanArtOrder(
            order_code=order_code,
            telegram_id=telegram_id,
            fan_art_id=fan_art.id,
            price_snapshot=Decimal(fan_art.price),
            status=PENDING_PAYMENT,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        result = await session.execute(
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .where(FanArtOrder.id == order.id)
        )
        return result.scalar_one()


async def set_waiting_receipt(order_id: int, telegram_id: int) -> FanArtOrder | None:
    async with AsyncSessionLocal() as session:
        order = await session.scalar(
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .where(
                FanArtOrder.id == order_id,
                FanArtOrder.telegram_id == telegram_id,
                FanArtOrder.status == PENDING_PAYMENT,
            )
        )
        if order is None:
            return None

        order.status = WAITING_RECEIPT
        await session.commit()

        result = await session.execute(
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .where(FanArtOrder.id == order_id)
        )
        return result.scalar_one()


async def attach_receipt(
    order_id: int,
    telegram_id: int,
    receipt_file_id: str,
) -> FanArtOrder | None:
    async with AsyncSessionLocal() as session:
        order = await session.scalar(
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .where(
                FanArtOrder.id == order_id,
                FanArtOrder.telegram_id == telegram_id,
                FanArtOrder.status == WAITING_RECEIPT,
            )
        )
        if order is None:
            return None

        order.receipt_file_id = receipt_file_id
        order.status = UNDER_REVIEW
        await session.commit()

        result = await session.execute(
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .where(FanArtOrder.id == order_id)
        )
        return result.scalar_one()


async def cancel_active_order(telegram_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        order = await session.scalar(
            select(FanArtOrder)
            .where(
                FanArtOrder.telegram_id == telegram_id,
                FanArtOrder.status.in_(ACTIVE_ORDER_STATUSES),
            )
            .order_by(FanArtOrder.id.desc())
            .limit(1)
        )
        if order is None:
            return False

        order.status = CANCELLED
        await session.commit()
        return True


async def approve_order(order_id: int) -> FanArtOrder | None:
    async with AsyncSessionLocal() as session:
        order = await session.scalar(
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .where(
                FanArtOrder.id == order_id,
                FanArtOrder.status == UNDER_REVIEW,
            )
        )
        if order is None:
            return None

        ownership = await session.scalar(
            select(FanArtOwnership.id)
            .where(
                FanArtOwnership.telegram_id == order.telegram_id,
                FanArtOwnership.fan_art_id == order.fan_art_id,
            )
            .limit(1)
        )

        if ownership is None:
            if order.fan_art.is_limited:
                if order.fan_art.stock is None or order.fan_art.stock <= 0:
                    raise ValueError("OUT_OF_STOCK")
                order.fan_art.stock -= 1

            session.add(
                FanArtOwnership(
                    telegram_id=order.telegram_id,
                    fan_art_id=order.fan_art_id,
                    order_id=order.id,
                )
            )

        order.status = APPROVED
        await session.commit()

        result = await session.execute(
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .where(FanArtOrder.id == order_id)
        )
        return result.scalar_one()


async def reject_order(order_id: int, reason: str) -> FanArtOrder | None:
    async with AsyncSessionLocal() as session:
        order = await session.scalar(
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .where(
                FanArtOrder.id == order_id,
                FanArtOrder.status == UNDER_REVIEW,
            )
        )
        if order is None:
            return None

        order.status = REJECTED
        order.rejection_reason = reason
        await session.commit()

        result = await session.execute(
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .where(FanArtOrder.id == order_id)
        )
        return result.scalar_one()


async def get_orders(status: str | None = None) -> list[FanArtOrder]:
    async with AsyncSessionLocal() as session:
        query = (
            select(FanArtOrder)
            .options(selectinload(FanArtOrder.fan_art))
            .order_by(FanArtOrder.id.desc())
        )
        if status is not None:
            query = query.where(FanArtOrder.status == status)

        result = await session.execute(query)
        return list(result.scalars().all())


async def sell_owned_fan_art(telegram_id: int, fan_art_id: int) -> tuple[bool, str]:
    """Sell an owned Fan Art for its configured in-game gold value."""
    async with AsyncSessionLocal() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == telegram_id).with_for_update())
        if character is None: return False, "قهرمان پیدا نشد."
        ownership = await session.scalar(select(FanArtOwnership).where(FanArtOwnership.telegram_id == telegram_id, FanArtOwnership.fan_art_id == fan_art_id).with_for_update())
        if ownership is None: return False, "این فن‌آرت در مجموعهٔ تو نیست."
        fan_art = await session.scalar(select(FanArt).where(FanArt.id == fan_art_id).with_for_update())
        if fan_art is None: return False, "فن‌آرت پیدا نشد."
        value = max(0, int(fan_art.value_gold or 0))
        if value <= 0: return False, "برای این فن‌آرت ارزش اقتصادی تعیین نشده است."
        old_gold = int(character.gold or 0)
        character.gold = min(2_147_483_647, old_gold + value)
        received = int(character.gold) - old_gold
        if character.active_fan_art_id == fan_art_id: character.active_fan_art_id = None
        name = fan_art.name
        await session.delete(ownership)
        await session.commit()
        return True, f"فن‌آرت «{name}» فروخته شد؛ +{received:,} طلا دریافت کردی."
