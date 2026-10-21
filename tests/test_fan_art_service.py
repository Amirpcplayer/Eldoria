# tests/test_fan_art_service.py

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from database.database import AsyncSessionLocal
from models.fan_art import FanArt, FanArtOrder, FanArtOwnership
from services.fan_art_service import (
    APPROVED,
    CANCELLED,
    PENDING_PAYMENT,
    REJECTED,
    UNDER_REVIEW,
    WAITING_RECEIPT,
    approve_order,
    attach_receipt,
    cancel_active_order,
    create_order,
    get_active_fan_arts,
    get_active_order,
    get_fan_art,
    get_owned_fan_arts,
    get_orders,
    owns_fan_art,
    reject_order,
    set_waiting_receipt,
)


TEST_TELEGRAM_ID = 987654321001
TEST_TELEGRAM_ID_2 = 987654321002


async def _cleanup():
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(FanArtOwnership).where(
                FanArtOwnership.telegram_id.in_(
                    [
                        TEST_TELEGRAM_ID,
                        TEST_TELEGRAM_ID_2,
                    ]
                )
            )
        )

        await session.execute(
            delete(FanArtOrder).where(
                FanArtOrder.telegram_id.in_(
                    [
                        TEST_TELEGRAM_ID,
                        TEST_TELEGRAM_ID_2,
                    ]
                )
            )
        )

        await session.execute(
            delete(FanArt).where(
                FanArt.name.like("TEST_FAN_ART_%")
            )
        )

        await session.commit()


async def _create_fan_art(
    *,
    name: str,
    price: Decimal = Decimal("10.00"),
    is_active: bool = True,
    is_limited: bool = False,
    stock: int | None = None,
    display_order: int = 0,
) -> int:
    async with AsyncSessionLocal() as session:
        fan_art = FanArt(
            name=name,
            description=f"Description for {name}",
            image_file_id=f"test_file_{name}",
            rarity="COMMON",
            price=price,
            is_active=is_active,
            is_limited=is_limited,
            stock=stock,
            display_order=display_order,
        )

        session.add(fan_art)
        await session.commit()
        await session.refresh(fan_art)

        return fan_art.id


@pytest.fixture(autouse=True)
async def cleanup_test_data():
    await _cleanup()
    yield
    await _cleanup()


@pytest.mark.asyncio
async def test_get_active_fan_arts_returns_only_active_items():
    inactive_id = await _create_fan_art(
        name="TEST_FAN_ART_INACTIVE",
        is_active=False,
    )

    active_id = await _create_fan_art(
        name="TEST_FAN_ART_ACTIVE",
        is_active=True,
        display_order=1,
    )

    fan_arts = await get_active_fan_arts()

    ids = [item.id for item in fan_arts]

    assert active_id in ids
    assert inactive_id not in ids


@pytest.mark.asyncio
async def test_get_fan_art_returns_existing_item():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_GET",
    )

    fan_art = await get_fan_art(fan_art_id)

    assert fan_art is not None
    assert fan_art.id == fan_art_id
    assert fan_art.name == "TEST_FAN_ART_GET"
    assert fan_art.price == Decimal("10.00")


@pytest.mark.asyncio
async def test_get_fan_art_returns_none_for_unknown_id():
    fan_art = await get_fan_art(999999999)

    assert fan_art is None


@pytest.mark.asyncio
async def test_owns_fan_art_is_false_before_purchase():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_OWNERSHIP_FALSE",
    )

    result = await owns_fan_art(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    assert result is False


@pytest.mark.asyncio
async def test_owns_fan_art_is_true_after_ownership_created():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_OWNERSHIP_TRUE",
    )

    async with AsyncSessionLocal() as session:
        ownership = FanArtOwnership(
            telegram_id=TEST_TELEGRAM_ID,
            fan_art_id=fan_art_id,
        )

        session.add(ownership)
        await session.commit()

    result = await owns_fan_art(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    assert result is True


@pytest.mark.asyncio
async def test_get_owned_fan_arts_returns_user_items():
    first_id = await _create_fan_art(
        name="TEST_FAN_ART_OWNED_1",
    )

    second_id = await _create_fan_art(
        name="TEST_FAN_ART_OWNED_2",
    )

    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                FanArtOwnership(
                    telegram_id=TEST_TELEGRAM_ID,
                    fan_art_id=first_id,
                ),
                FanArtOwnership(
                    telegram_id=TEST_TELEGRAM_ID,
                    fan_art_id=second_id,
                ),
            ]
        )

        await session.commit()

    owned = await get_owned_fan_arts(TEST_TELEGRAM_ID)

    owned_ids = {item.id for item in owned}

    assert first_id in owned_ids
    assert second_id in owned_ids


@pytest.mark.asyncio
async def test_create_order_creates_pending_order():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_CREATE_ORDER",
        price=Decimal("25.50"),
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    assert order.id is not None
    assert order.telegram_id == TEST_TELEGRAM_ID
    assert order.fan_art_id == fan_art_id
    assert order.status == PENDING_PAYMENT
    assert order.price_snapshot == Decimal("25.50")
    assert order.order_code.startswith("ELD-")
    assert order.fan_art is not None
    assert order.fan_art.id == fan_art_id


@pytest.mark.asyncio
async def test_get_active_order_returns_created_order():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_ACTIVE_ORDER",
    )

    created = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    active = await get_active_order(TEST_TELEGRAM_ID)

    assert active is not None
    assert active.id == created.id
    assert active.status == PENDING_PAYMENT
    assert active.fan_art is not None
    assert active.fan_art.id == fan_art_id


@pytest.mark.asyncio
async def test_create_order_blocks_second_active_order():
    first_id = await _create_fan_art(
        name="TEST_FAN_ART_ORDER_FIRST",
    )

    second_id = await _create_fan_art(
        name="TEST_FAN_ART_ORDER_SECOND",
    )

    await create_order(
        TEST_TELEGRAM_ID,
        first_id,
    )

    with pytest.raises(ValueError, match="ACTIVE_ORDER_EXISTS"):
        await create_order(
            TEST_TELEGRAM_ID,
            second_id,
        )


@pytest.mark.asyncio
async def test_create_order_rejects_inactive_fan_art():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_ORDER_INACTIVE",
        is_active=False,
    )

    with pytest.raises(ValueError, match="FAN_ART_NOT_FOUND"):
        await create_order(
            TEST_TELEGRAM_ID,
            fan_art_id,
        )


@pytest.mark.asyncio
async def test_create_order_rejects_out_of_stock_limited_fan_art():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_OUT_OF_STOCK",
        is_limited=True,
        stock=0,
    )

    with pytest.raises(ValueError, match="OUT_OF_STOCK"):
        await create_order(
            TEST_TELEGRAM_ID,
            fan_art_id,
        )


@pytest.mark.asyncio
async def test_create_order_rejects_already_owned_fan_art():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_ALREADY_OWNED",
    )

    async with AsyncSessionLocal() as session:
        session.add(
            FanArtOwnership(
                telegram_id=TEST_TELEGRAM_ID,
                fan_art_id=fan_art_id,
            )
        )

        await session.commit()

    with pytest.raises(ValueError, match="ALREADY_OWNED"):
        await create_order(
            TEST_TELEGRAM_ID,
            fan_art_id,
        )


@pytest.mark.asyncio
async def test_set_waiting_receipt_changes_status():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_WAITING",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    updated = await set_waiting_receipt(
        order.id,
        TEST_TELEGRAM_ID,
    )

    assert updated is not None
    assert updated.status == WAITING_RECEIPT


@pytest.mark.asyncio
async def test_set_waiting_receipt_rejects_wrong_user():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_WAITING_WRONG_USER",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    result = await set_waiting_receipt(
        order.id,
        TEST_TELEGRAM_ID_2,
    )

    assert result is None


@pytest.mark.asyncio
async def test_attach_receipt_changes_status_and_saves_file_id():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_RECEIPT",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    await set_waiting_receipt(
        order.id,
        TEST_TELEGRAM_ID,
    )

    updated = await attach_receipt(
        order.id,
        TEST_TELEGRAM_ID,
        "TEST_RECEIPT_FILE_ID",
    )

    assert updated is not None
    assert updated.status == UNDER_REVIEW
    assert updated.receipt_file_id == "TEST_RECEIPT_FILE_ID"


@pytest.mark.asyncio
async def test_attach_receipt_rejects_wrong_user():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_RECEIPT_WRONG_USER",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    await set_waiting_receipt(
        order.id,
        TEST_TELEGRAM_ID,
    )

    result = await attach_receipt(
        order.id,
        TEST_TELEGRAM_ID_2,
        "TEST_RECEIPT_FILE_ID",
    )

    assert result is None


@pytest.mark.asyncio
async def test_cancel_active_order_changes_status():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_CANCEL",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    result = await cancel_active_order(
        TEST_TELEGRAM_ID,
    )

    assert result is True

    async with AsyncSessionLocal() as session:
        db_order = await session.get(
            FanArtOrder,
            order.id,
        )

        assert db_order is not None
        assert db_order.status == CANCELLED


@pytest.mark.asyncio
async def test_cancel_active_order_returns_false_without_order():
    result = await cancel_active_order(
        TEST_TELEGRAM_ID,
    )

    assert result is False


@pytest.mark.asyncio
async def test_approve_order_creates_ownership():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_APPROVE",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    await set_waiting_receipt(
        order.id,
        TEST_TELEGRAM_ID,
    )

    await attach_receipt(
        order.id,
        TEST_TELEGRAM_ID,
        "TEST_RECEIPT_APPROVE",
    )

    approved = await approve_order(order.id)

    assert approved is not None
    assert approved.status == APPROVED

    owned = await owns_fan_art(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    assert owned is True


@pytest.mark.asyncio
async def test_approve_limited_order_decreases_stock():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_LIMITED",
        is_limited=True,
        stock=3,
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    await set_waiting_receipt(
        order.id,
        TEST_TELEGRAM_ID,
    )

    await attach_receipt(
        order.id,
        TEST_TELEGRAM_ID,
        "TEST_RECEIPT_LIMITED",
    )

    await approve_order(order.id)

    async with AsyncSessionLocal() as session:
        fan_art = await session.get(
            FanArt,
            fan_art_id,
        )

        assert fan_art is not None
        assert fan_art.stock == 2


@pytest.mark.asyncio
async def test_approve_order_returns_none_when_not_under_review():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_APPROVE_INVALID_STATUS",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    result = await approve_order(order.id)

    assert result is None


@pytest.mark.asyncio
async def test_reject_order_changes_status_and_saves_reason():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_REJECT",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    await set_waiting_receipt(
        order.id,
        TEST_TELEGRAM_ID,
    )

    await attach_receipt(
        order.id,
        TEST_TELEGRAM_ID,
        "TEST_RECEIPT_REJECT",
    )

    rejected = await reject_order(
        order.id,
        "TEST_REASON",
    )

    assert rejected is not None
    assert rejected.status == REJECTED
    assert rejected.rejection_reason == "TEST_REASON"


@pytest.mark.asyncio
async def test_reject_order_returns_none_when_not_under_review():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_REJECT_INVALID_STATUS",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    result = await reject_order(
        order.id,
        "TEST_REASON",
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_orders_returns_orders():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_GET_ORDERS",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    orders = await get_orders()

    ids = [item.id for item in orders]

    assert order.id in ids


@pytest.mark.asyncio
async def test_get_orders_can_filter_by_status():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_FILTER_STATUS",
    )

    order = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    pending_orders = await get_orders(
        PENDING_PAYMENT,
    )

    pending_ids = [item.id for item in pending_orders]

    assert order.id in pending_ids

    approved_orders = await get_orders(
        APPROVED,
    )

    approved_ids = [item.id for item in approved_orders]

    assert order.id not in approved_ids


@pytest.mark.asyncio
async def test_full_purchase_flow():
    fan_art_id = await _create_fan_art(
        name="TEST_FAN_ART_FULL_FLOW",
        price=Decimal("99.99"),
    )

    created = await create_order(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    assert created.status == PENDING_PAYMENT

    waiting = await set_waiting_receipt(
        created.id,
        TEST_TELEGRAM_ID,
    )

    assert waiting is not None
    assert waiting.status == WAITING_RECEIPT

    review = await attach_receipt(
        created.id,
        TEST_TELEGRAM_ID,
        "TEST_FULL_FLOW_RECEIPT",
    )

    assert review is not None
    assert review.status == UNDER_REVIEW

    approved = await approve_order(
        created.id,
    )

    assert approved is not None
    assert approved.status == APPROVED

    assert await owns_fan_art(
        TEST_TELEGRAM_ID,
        fan_art_id,
    )

    active_order = await get_active_order(
        TEST_TELEGRAM_ID,
    )

    assert active_order is None