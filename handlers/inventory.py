from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from sqlalchemy import select

from bot.bot import bot
from database.database import AsyncSessionLocal
from models.character import Character
from models.inventory import Inventory
from models.item import Item
from models.trade import Trade

from keyboards.inventory import (
    inventory_keyboard,
    inventory_items_keyboard,
)
from keyboards.item import (
    item_details_keyboard,
    trade_request_keyboard,
)
from services.inventory_service import sell_item
from states.character import PlayerTrade


router = Router()


# ============================================================
# INVENTORY MENU
# ============================================================

@router.callback_query(
    F.data == "menu:inventory"
)
async def inventory_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == callback.from_user.id
            )
        )

    if character is None:
        await callback.message.edit_text(
            "❌ قهرمان پیدا نشد."
        )
        return

    await callback.message.edit_text(
        "🗝️ صندوقچه قهرمان\n\n"
        f"👤 {character.name}\n\n"
        "📦 دسته‌بندی آیتم‌ها را انتخاب کنید:",
        reply_markup=inventory_keyboard(),
    )


# ============================================================
# INVENTORY CATEGORY
# ============================================================

@router.callback_query(
    F.data.startswith("inventory:")
)
async def inventory_category_handler(
    callback: CallbackQuery,
):

    category = callback.data.split(":")[1]

    type_map = {
        "equipment": "equipment",
        "potions": "potion",
        "materials": "material",
        "scrolls": "scroll",
        "fanart": "fan_art",
    }

    if category not in type_map:
        await callback.answer(
            "⚠️ این بخش هنوز آماده نشده است.",
            show_alert=True,
        )
        return

    item_type = type_map[category]

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == callback.from_user.id
            )
        )

        if character is None:
            await callback.answer(
                "❌ قهرمان پیدا نشد.",
                show_alert=True,
            )
            return

        result = await session.execute(
            select(Inventory, Item)
            .join(
                Item,
                Inventory.item_id == Item.id,
            )
            .where(
                Inventory.character_id == character.id,
                Item.item_type == item_type,
                Inventory.quantity > 0,
            )
            .order_by(Inventory.id)
        )

        items = list(result.all())

    await callback.message.edit_text(
        "🗝️ صندوقچه قهرمان\n\n"
        f"👤 {character.name}\n\n"
        "📦 آیتم‌های این بخش:",
        reply_markup=inventory_items_keyboard(items),
    )

    await callback.answer()


# ============================================================
# ITEM DETAILS
# ============================================================

@router.callback_query(
    F.data.startswith("item:")
)
async def item_details_handler(
    callback: CallbackQuery,
):

    parts = callback.data.split(":")

    # item:sell / item:sell_player را این Handler نباید بگیرد
    if len(parts) != 2:
        return

    try:
        item_id = int(parts[1])
    except ValueError:
        await callback.answer(
            "❌ آیتم نامعتبر است.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == callback.from_user.id
            )
        )

        if character is None:
            await callback.answer(
                "❌ قهرمان پیدا نشد.",
                show_alert=True,
            )
            return

        row = await session.execute(
            select(Inventory, Item)
            .join(
                Item,
                Inventory.item_id == Item.id,
            )
            .where(
                Inventory.character_id == character.id,
                Inventory.item_id == item_id,
                Inventory.quantity > 0,
            )
        )

        row = row.first()

    if row is None:
        await callback.answer(
            "❌ این آیتم در صندوقچه شما وجود ندارد.",
            show_alert=True,
        )
        return

    inventory_item, item = row

    await callback.message.edit_text(
        f"📦 {item.name}\n\n"
        f"📊 تعداد: {inventory_item.quantity}\n"
        f"💰 قیمت فروش: {item.sell_price} Gold",
        reply_markup=item_details_keyboard(item.id),
    )

    await callback.answer()


# ============================================================
# SELL TO SHOP
# ============================================================

@router.callback_query(
    F.data.startswith("item:sell:")
)
async def sell_item_handler(
    callback: CallbackQuery,
):

    try:
        item_id = int(
            callback.data.split(":")[2]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "❌ آیتم نامعتبر است.",
            show_alert=True,
        )
        return

    success, message = await sell_item(
        callback.from_user.id,
        item_id,
        1,
    )

    await callback.answer(
        message,
        show_alert=True,
    )

    if not success:
        return

    await inventory_handler(callback)


# ============================================================
# SELL TO PLAYER
# ============================================================

@router.callback_query(
    F.data.startswith("item:sell_player:")
)
async def sell_to_player_handler(
    callback: CallbackQuery,
    state: FSMContext,
):

    try:
        item_id = int(
            callback.data.split(":")[2]
        )
    except (ValueError, IndexError):
        await callback.answer(
            "❌ آیتم نامعتبر است.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == callback.from_user.id
            )
        )

        if character is None:
            await callback.answer(
                "❌ قهرمان پیدا نشد.",
                show_alert=True,
            )
            return

        inventory_item = await session.scalar(
            select(Inventory).where(
                Inventory.character_id == character.id,
                Inventory.item_id == item_id,
                Inventory.quantity > 0,
            )
        )

        item = await session.scalar(
            select(Item).where(
                Item.id == item_id
            )
        )

    if inventory_item is None or item is None:
        await callback.answer(
            "❌ این آیتم در صندوقچه شما وجود ندارد.",
            show_alert=True,
        )
        return

    if not item.is_tradeable:
        await callback.answer(
            "🔒 این آیتم قابل معامله نیست.",
            show_alert=True,
        )
        return

    await state.update_data(
        item_id=item_id
    )

    await state.set_state(
        PlayerTrade.waiting_for_target
    )

    await callback.message.edit_text(
        "👤 فروش به بازیکن\n\n"
        f"📦 آیتم: {item.name}\n"
        f"📊 تعداد: 1\n\n"
        "لطفاً نام قهرمان یا شناسه بازیکن خریدار را وارد کنید."
    )

    await callback.answer()


# ============================================================
# PLAYER TRADE - TARGET
# ============================================================

@router.message(
    PlayerTrade.waiting_for_target
)
async def trade_target_handler(
    message: Message,
    state: FSMContext,
):

    if not message.text:
        await message.answer(
            "⚠️ لطفاً نام قهرمان یا شناسه بازیکن را وارد کنید."
        )
        return

    target_text = message.text.strip()

    if not target_text:
        await message.answer(
            "⚠️ لطفاً نام قهرمان یا شناسه بازیکن را وارد کنید."
        )
        return

    async with AsyncSessionLocal() as session:

        buyer = None

        if target_text.isdigit():

            buyer = await session.scalar(
                select(Character).where(
                    Character.telegram_id == int(target_text)
                )
            )

        else:

            username = target_text.lstrip("@")

            buyer = await session.scalar(
                select(Character).where(
                    Character.name == username
                )
            )

    if buyer is None:
        await message.answer(
            "🌫️ قهرمان موردنظر در سرزمین اِلدوریا پیدا نشد.\n\n"
            "🔎 نام یا شناسه بازیکن را بررسی کنید."
        )
        return

    if buyer.telegram_id == message.from_user.id:
        await message.answer(
            "⚠️ نمی‌توانی از خودت خرید کنی!\n\n"
            "👤 یک بازیکن دیگر را انتخاب کن."
        )
        return

    await state.update_data(
        buyer_telegram_id=buyer.telegram_id
    )

    await state.set_state(
        PlayerTrade.waiting_for_price
    )

    await message.answer(
        "💰 قیمت معامله را وارد کنید.\n\n"
        "مثال:\n"
        "50\n\n"
        "💰 مبلغ باید به صورت عدد وارد شود."
    )


# ============================================================
# PLAYER TRADE - PRICE
# ============================================================

@router.message(
    PlayerTrade.waiting_for_price
)
async def trade_price_handler(
    message: Message,
    state: FSMContext,
):

    if not message.text:
        await message.answer(
            "💰 مبلغ معامله را به صورت عدد وارد کنید."
        )
        return

    price_text = message.text.strip()

    if not price_text.isdigit():
        await message.answer(
            "💰 مبلغ معامله باید فقط به صورت عدد وارد شود."
        )
        return

    price = int(price_text)

    if price <= 0:
        await message.answer(
            "⚠️ قیمت معامله باید بیشتر از صفر باشد."
        )
        return

    data = await state.get_data()

    item_id = data.get("item_id")
    buyer_telegram_id = data.get(
        "buyer_telegram_id"
    )

    if not item_id or not buyer_telegram_id:
        await state.clear()

        await message.answer(
            "⚠️ اطلاعات معامله ناقص است.\n\n"
            "لطفاً معامله را دوباره از صندوقچه شروع کنید."
        )
        return

    seller_telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:

        seller = await session.scalar(
            select(Character).where(
                Character.telegram_id == seller_telegram_id
            )
        )

        buyer = await session.scalar(
            select(Character).where(
                Character.telegram_id == buyer_telegram_id
            )
        )

        item = await session.scalar(
            select(Item).where(
                Item.id == item_id
            )
        )

        if seller is None or buyer is None:
            await state.clear()

            await message.answer(
                "🌫️ یکی از قهرمانان پیدا نشد."
            )
            return

        if item is None:
            await state.clear()

            await message.answer(
                "📦 آیتم موردنظر پیدا نشد."
            )
            return

        if not item.is_tradeable:
            await state.clear()

            await message.answer(
                "🔒 این آیتم قابل معامله نیست."
            )
            return

        seller_inventory = await session.scalar(
            select(Inventory).where(
                Inventory.character_id == seller.id,
                Inventory.item_id == item_id,
            )
        )

        if (
            seller_inventory is None
            or seller_inventory.quantity < 1
        ):
            await state.clear()

            await message.answer(
                "🗝️ این آیتم در صندوقچه قهرمانت وجود ندارد.\n\n"
                "ممکن است قبلاً فروخته یا معامله شده باشد."
            )
            return

        trade = Trade(
            seller_telegram_id=seller_telegram_id,
            buyer_telegram_id=buyer_telegram_id,
            item_id=item_id,
            quantity=1,
            price=price,
            status="pending",
        )

        session.add(trade)

        await session.flush()

        trade_id = trade.id

        await session.commit()

    await state.clear()

    await message.answer(
        "📨 پیشنهاد معامله ارسال شد!\n\n"
        f"📦 آیتم: {item.name}\n"
        "📊 تعداد: 1\n"
        f"💰 قیمت: {price} Gold\n\n"
        "⏳ منتظر پاسخ خریدار بمان."
    )

    try:
        await bot.send_message(
            buyer_telegram_id,
            "📨 یک پیشنهاد معامله جدید داری!\n\n"
            f"👤 فروشنده: {seller.name}\n"
            f"📦 آیتم: {item.name}\n"
            "📊 تعداد: 1\n"
            f"💰 قیمت: {price} Gold\n\n"
            "⚔️ سرنوشت این معامله در دستان توست!",
            reply_markup=trade_request_keyboard(
                str(trade_id)
            ),
        )
    except Exception:
        pass


# ============================================================
# ACCEPT TRADE
# ============================================================

@router.callback_query(
    F.data.startswith("trade:accept:")
)
async def accept_trade_handler(
    callback: CallbackQuery,
):

    try:
        trade_id = int(
            callback.data.split(":")[2]
        )
    except (ValueError, IndexError):

        await callback.answer(
            "⚠️ این پیشنهاد معامله معتبر نیست.",
            show_alert=True,
        )
        return

    buyer_user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:

        trade = await session.scalar(
            select(Trade)
            .where(Trade.id == trade_id)
            .with_for_update()
        )

        if trade is None:
            await callback.answer(
                "🌫️ این معامله پیدا نشد.",
                show_alert=True,
            )
            return

        if trade.buyer_telegram_id != buyer_user_id:
            await callback.answer(
                "🔒 این پیشنهاد برای بازیکن دیگری است!",
                show_alert=True,
            )
            return

        if trade.status != "pending":
            await callback.answer(
                "⚠️ این پیشنهاد دیگر فعال نیست.",
                show_alert=True,
            )
            return

        seller_user_id = trade.seller_telegram_id

        seller = await session.scalar(
            select(Character)
            .where(
                Character.telegram_id == seller_user_id
            )
            .with_for_update()
        )

        buyer = await session.scalar(
            select(Character)
            .where(
                Character.telegram_id == buyer_user_id
            )
            .with_for_update()
        )

        item = await session.scalar(
            select(Item).where(
                Item.id == trade.item_id
            )
        )

        if seller is None or buyer is None:
            await callback.answer(
                "🌫️ اطلاعات یکی از قهرمانان پیدا نشد.",
                show_alert=True,
            )
            return

        if item is None:
            await callback.answer(
                "📦 آیتم معامله پیدا نشد.",
                show_alert=True,
            )
            return

        if not item.is_tradeable:
            await callback.answer(
                "🔒 این آیتم دیگر قابل معامله نیست.",
                show_alert=True,
            )
            return

        if buyer.gold < trade.price:

            needed_gold = trade.price - buyer.gold

            await callback.answer(
                f"💰 Gold کافی نداری!\n\n"
                f"📦 آیتم: {item.name}\n"
                f"💰 قیمت: {trade.price} Gold\n"
                f"💰 موجودی تو: {buyer.gold} Gold\n\n"
                f"⚠️ {needed_gold} Gold دیگر نیاز داری.",
                show_alert=True,
            )
            return

        seller_inventory = await session.scalar(
            select(Inventory)
            .where(
                Inventory.character_id == seller.id,
                Inventory.item_id == trade.item_id,
            )
            .with_for_update()
        )

        if (
            seller_inventory is None
            or seller_inventory.quantity < trade.quantity
        ):

            trade.status = "cancelled"

            await session.commit()

            await callback.message.edit_text(
                "⚠️ معامله لغو شد!\n\n"
                f"📦 آیتم «{item.name}» دیگر در صندوقچه فروشنده موجود نیست.\n\n"
                "💰 هیچ Goldای منتقل نشد."
            )

            try:
                await bot.send_message(
                    seller_user_id,
                    "⚠️ معامله لغو شد!\n\n"
                    f"📦 آیتم «{item.name}» دیگر در صندوقچه تو موجود نیست.\n\n"
                    "💰 هیچ Goldای منتقل نشد.",
                )
            except Exception:
                pass

            await callback.answer(
                "📦 آیتم دیگر موجود نیست.",
                show_alert=True,
            )
            return

        buyer_inventory = await session.scalar(
            select(Inventory)
            .where(
                Inventory.character_id == buyer.id,
                Inventory.item_id == trade.item_id,
            )
            .with_for_update()
        )

        seller_inventory.quantity -= trade.quantity

        if seller_inventory.quantity <= 0:
            await session.delete(
                seller_inventory
            )

        if buyer_inventory:

            buyer_inventory.quantity += trade.quantity

        else:

            buyer_inventory = Inventory(
                character_id=buyer.id,
                item_id=trade.item_id,
                quantity=trade.quantity,
            )

            session.add(
                buyer_inventory
            )

        buyer.gold -= trade.price
        seller.gold += trade.price

        trade.status = "accepted"

        seller_current_gold = seller.gold
        buyer_current_gold = buyer.gold

        await session.commit()

    await callback.message.edit_text(
        "🎉 معامله با موفقیت انجام شد!\n\n"
        f"📦 آیتم دریافت‌شده: {item.name}\n"
        f"📊 تعداد: {trade.quantity}\n\n"
        f"💰 پرداخت کردی: {trade.price} Gold\n"
        f"💰 Gold باقی‌مانده: {buyer_current_gold}"
    )

    try:
        await bot.send_message(
            seller_user_id,
            "🎉 معامله با موفقیت انجام شد!\n\n"
            f"📦 آیتم فروخته‌شده: {item.name}\n"
            f"📊 تعداد: {trade.quantity}\n\n"
            f"💰 دریافت کردی: +{trade.price} Gold\n"
            f"💰 Gold فعلی: {seller_current_gold}",
        )
    except Exception:
        pass

    await callback.answer(
        "🎉 معامله با موفقیت انجام شد!"
    )


# ============================================================
# REJECT TRADE
# ============================================================

@router.callback_query(
    F.data.startswith("trade:reject:")
)
async def reject_trade_handler(
    callback: CallbackQuery,
):

    try:
        trade_id = int(
            callback.data.split(":")[2]
        )
    except (ValueError, IndexError):

        await callback.answer(
            "⚠️ این پیشنهاد معامله معتبر نیست.",
            show_alert=True,
        )
        return

    buyer_user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:

        trade = await session.scalar(
            select(Trade)
            .where(Trade.id == trade_id)
            .with_for_update()
        )

        if trade is None:
            await callback.answer(
                "🌫️ این معامله پیدا نشد.",
                show_alert=True,
            )
            return

        if trade.buyer_telegram_id != buyer_user_id:
            await callback.answer(
                "🔒 این پیشنهاد برای بازیکن دیگری است!",
                show_alert=True,
            )
            return

        if trade.status != "pending":
            await callback.answer(
                "⚠️ این پیشنهاد دیگر فعال نیست.",
                show_alert=True,
            )
            return

        seller_user_id = trade.seller_telegram_id

        item = await session.scalar(
            select(Item).where(
                Item.id == trade.item_id
            )
        )

        trade.status = "rejected"

        await session.commit()

    await callback.message.edit_text(
        "🛑 معامله رد شد.\n\n"
        f"📦 آیتم: {item.name if item else 'نامشخص'}\n"
        "💰 هیچ Goldای منتقل نشد."
    )

    try:
        await bot.send_message(
            seller_user_id,
            "🛑 پیشنهاد معامله رد شد.\n\n"
            f"📦 آیتم: {item.name if item else 'نامشخص'}\n"
            "💰 هیچ Goldای منتقل نشد.",
        )
    except Exception:
        pass

    await callback.answer(
        "🛑 معامله رد شد."
    )