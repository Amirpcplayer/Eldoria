import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from bot.bot import bot
from database.database import AsyncSessionLocal

from models.character import Character
from models.inventory import Inventory
from models.item import Item
from models.trade import Trade
from models.equipment import CharacterEquipment, Equipment

from services.fan_art_service import get_owned_fan_arts
from services.inventory_service import sell_item
from services.scroll_service import scroll_kind, SCROLLS, activate_scroll, has_buff, get_buff
from services.equipment_service import (
    equip_equipment,
    unequip_equipment,
)

from services.panel_image_service import show_panel

from keyboards.inventory import (
    inventory_keyboard,
    inventory_items_keyboard,
    equipment_items_keyboard,
    fan_art_inventory_keyboard,
)

from keyboards.item import (
    item_details_keyboard,
    trade_request_keyboard,
)

from states.character import PlayerTrade


router = Router()
logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _normalize_digits(value: str) -> str:
    translation = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )
    return value.translate(translation)


def _normalize_username(value: str | None) -> str:
    if not value:
        return ""

    value = value.strip()

    if value.startswith("@"):
        value = value[1:]

    return value.strip().lower()


async def _get_character(telegram_id: int):
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )


async def _show(
    callback: CallbackQuery,
    text: str,
    reply_markup=None,
) -> bool:
    """
    تمام پنل‌های Inventory از inventory.jpg استفاده می‌کنند.

    این تابع فقط یک wrapper برای show_panel است تا منطق
    قدیمی inventory نیازی به تغییر گسترده نداشته باشد.
    """

    try:
        await show_panel(
            callback=callback,
            panel_name="inventory",
            text=text,
            reply_markup=reply_markup,
        )
        return True

    except Exception:
        logger.exception(
            "Failed to render inventory panel for telegram_id=%s",
            callback.from_user.id,
        )
        try:
            await callback.answer(
                "❌ باز کردن صندوقچه با خطا روبه‌رو شد. جزئیات در لاگ ربات ثبت شد.",
                show_alert=True,
            )
        except Exception:
            pass
        return False


def _equipment_detail_keyboard(
    equipment_id: int,
    equipped: bool,
) -> InlineKeyboardMarkup:

    if equipped:
        action_button = InlineKeyboardButton(
            text="🔓 خارج کردن از تجهیزات",
            callback_data=f"inventory:unequip:{equipment_id}",
        )
    else:
        action_button = InlineKeyboardButton(
            text="⚔️ تجهیز کردن",
            callback_data=f"inventory:equip:{equipment_id}",
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [action_button],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به تجهیزات",
                    callback_data="inventory:equipment",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗃 بازگشت به صندوقچه",
                    callback_data="menu:inventory",
                )
            ],
        ]
    )


async def _render_equipment_details(
    callback: CallbackQuery,
    equipment_id: int,
) -> bool:

    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            return False

        result = await session.execute(
            select(
                CharacterEquipment,
                Equipment,
            )
            .join(
                Equipment,
                CharacterEquipment.equipment_id == Equipment.id,
            )
            .where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipment_id == equipment_id,
                CharacterEquipment.quantity > 0,
                Equipment.is_active.is_(True),
            )
        )

        row = result.first()

    if row is None:
        return False

    owned, equipment = row

    description = (
        equipment.description
        or "توضیحی برای این تجهیزات ثبت نشده است."
    )

    text = (
        f"⚔️ {equipment.name}\n\n"
        f"{description}\n\n"
        f"📌 نوع: {equipment.equipment_type}\n"
        f"💎 کمیابی: {equipment.rarity}\n"
        f"🔢 تعداد: {owned.quantity}\n\n"
        f"⚔️ حمله: +{equipment.attack}\n"
        f"✨ قدرت جادو: +{equipment.magic_power}\n"
        f"🛡️ دفاع: +{equipment.defense}\n"
        f"🔮 دفاع جادویی: +{equipment.magic_defense}\n"
        f"❤️ HP: +{equipment.hp}\n"
        f"💧 Mana: +{equipment.mana}\n"
        f"💨 سرعت: +{equipment.speed}\n"
        f"🎯 دقت: +{equipment.accuracy}\n"
        f"💥 کریتیکال: +{equipment.critical}\n\n"
        f"{'✅ در حال استفاده' if owned.equipped else '🗃 در صندوقچه'}"
    )

    return await _show(
        callback,
        text,
        _equipment_detail_keyboard(
            equipment.id,
            owned.equipped,
        ),
    )


# ============================================================
# Inventory Main
# ============================================================

@router.callback_query(F.data == "menu:inventory")
async def inventory_handler(
    callback: CallbackQuery,
):
    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            await callback.answer(
                "❌ شخصیت شما پیدا نشد.",
                show_alert=True,
            )
            return

        username = _normalize_username(
            callback.from_user.username
        )

        if username:
            character.telegram_username = username
            await session.commit()

        character_name = character.name

    await _show(
        callback,
        (
            "🗃 <b>صندوقچه قهرمان</b>\n\n"
            f"👤 {character_name}\n\n"
            "دسته‌بندی موردنظر را انتخاب کنید:"
        ),
        inventory_keyboard(),
    )

    await callback.answer()


# ============================================================
# Inventory Categories
# ============================================================

@router.callback_query(
    F.data.in_(
        {
            "inventory:equipment",
            "inventory:potions",
            "inventory:materials",
            "inventory:scrolls",
            "inventory:fanart",
            "inventory:all",
        }
    )
)
async def inventory_category_handler(
    callback: CallbackQuery,
):
    category = callback.data.split(":")[1]
    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            await callback.answer(
                "❌ شخصیت شما پیدا نشد.",
                show_alert=True,
            )
            return

        username = _normalize_username(
            callback.from_user.username
        )

        if username:
            character.telegram_username = username
            await session.commit()

        if category == "all":
            item_result = await session.execute(
                select(Inventory, Item)
                .join(Item, Inventory.item_id == Item.id)
                .where(
                    Inventory.character_id == character.id,
                    Inventory.quantity > 0,
                )
                .order_by(Item.item_type, Item.name, Inventory.id)
            )
            owned_items = list(item_result.all())

            equipment_result = await session.execute(
                select(CharacterEquipment, Equipment)
                .join(Equipment, CharacterEquipment.equipment_id == Equipment.id)
                .where(
                    CharacterEquipment.character_id == character.id,
                    CharacterEquipment.quantity > 0,
                    Equipment.is_active.is_(True),
                )
                .order_by(Equipment.name, CharacterEquipment.id)
            )
            owned_equipment = list(equipment_result.all())

            text_lines = ["📦 <b>تمام آیتم‌های واقعی صندوقچه</b>", ""]
            buttons = []
            if owned_items:
                text_lines.append("🗃 <b>آیتم‌ها</b>")
                for inv_item, item in owned_items:
                    text_lines.append(f"• {item.name} × {inv_item.quantity}")
                    buttons.append([InlineKeyboardButton(
                        text=f"{item.name} × {inv_item.quantity}",
                        callback_data=f"item:{item.id}",
                    )])
            if owned_equipment:
                text_lines.extend(["", "⚔️ <b>تجهیزات</b>"])
                for owned, equipment in owned_equipment:
                    suffix = " · مجهز" if owned.equipped else ""
                    text_lines.append(f"• {equipment.name} × {owned.quantity}{suffix}")
                    buttons.append([InlineKeyboardButton(
                        text=f"{equipment.name} × {owned.quantity}{' ✅' if owned.equipped else ''}",
                        callback_data=f"equipmentitem:{equipment.id}",
                    )])
            if not owned_items and not owned_equipment:
                text_lines.append("📭 صندوقچه‌ات فعلاً خالی است.")
            buttons.append([InlineKeyboardButton(
                text="🔙 بازگشت به صندوقچه",
                callback_data="menu:inventory",
            )])
            text = "\n".join(text_lines)
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        elif category == "equipment":

            result = await session.execute(
                select(
                    CharacterEquipment,
                    Equipment,
                )
                .join(
                    Equipment,
                    CharacterEquipment.equipment_id == Equipment.id,
                )
                .where(
                    CharacterEquipment.character_id == character.id,
                    CharacterEquipment.quantity > 0,
                    Equipment.is_active.is_(True),
                )
                .order_by(CharacterEquipment.id)
            )

            items = list(result.all())

            text = (
                "⚔️ <b>تجهیزات موجود در صندوقچه</b>\n\n"
                "برای مشاهده جزئیات روی یکی از تجهیزات بزنید."
            )

            keyboard = equipment_items_keyboard(items)

        elif category == "fanart":

            owned_fan_arts = await get_owned_fan_arts(
                telegram_id
            )

            text = (
                "🎨 <b>فن‌آرت‌های صندوقچه</b>\n\n"
                "فن‌آرت موردنظر را انتخاب کنید:"
            )

            keyboard = fan_art_inventory_keyboard(
                owned_fan_arts
            )

        else:

            type_map = {
                "potions": "potion",
                "materials": "material",
                "scrolls": "scroll",
            }

            item_type = type_map[category]

            result = await session.execute(
                select(
                    Inventory,
                    Item,
                )
                .join(
                    Item,
                    Inventory.item_id == Item.id,
                )
                .where(
                    Inventory.character_id == character.id,
                    Inventory.quantity > 0,
                    Item.item_type == item_type,
                )
                .order_by(Inventory.id)
            )

            items = list(result.all())

            labels = {
                "potions": "🧪 <b>معجون‌های صندوقچه</b>",
                "materials": "🗃 <b>متریال‌های صندوقچه</b>",
                "scrolls": "📜 <b>اسکرول‌های صندوقچه</b>",
            }

            text = labels[category]

            keyboard = inventory_items_keyboard(items)

    await _show(
        callback,
        text,
        keyboard,
    )

    await callback.answer()


# ============================================================
# Empty / No-op
# ============================================================

@router.callback_query(F.data == "inventory:noop")
async def inventory_noop_handler(
    callback: CallbackQuery,
):
    await callback.answer(
        "موردی برای نمایش در این بخش وجود ندارد."
    )


# ============================================================
# Item Details
# ============================================================

@router.callback_query(
    F.data.regexp(r"^item:\d+$")
)
async def item_details_handler(
    callback: CallbackQuery,
):
    item_id = int(
        callback.data.split(":")[1]
    )

    telegram_id = callback.from_user.id

    async with AsyncSessionLocal() as session:

        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == telegram_id
            )
        )

        if character is None:
            await callback.answer(
                "❌ شخصیت شما پیدا نشد.",
                show_alert=True,
            )
            return

        username = _normalize_username(
            callback.from_user.username
        )

        if username:
            character.telegram_username = username
            await session.commit()

        result = await session.execute(
            select(
                Inventory,
                Item,
            )
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

        row = result.first()

    if row is None:
        await callback.answer(
            "❌ این آیتم در صندوقچه شما نیست.",
            show_alert=True,
        )
        return

    inventory_item, item = row

    description = (
        item.description
        or "توضیحی برای این آیتم ثبت نشده است."
    )

    text = (
        f"🗃 <b>{item.name}</b>\n\n"
        f"{description}\n\n"
        f"🔢 تعداد: {inventory_item.quantity}\n"
        f"💰 قیمت فروش: {item.sell_price:,} Gold"
    )

    if item.item_type == "scroll" and scroll_kind(item.name):
        kind = scroll_kind(item.name)
        active_buff = await get_buff(telegram_id, kind)
        active = active_buff is not None
        if active_buff:
            remaining = max(1, int(float(active_buff.get("expires_at", 0)) - datetime.utcnow().timestamp()))
            hours, minutes = divmod(remaining // 60, 60)
            text += f"\n\n⏳ <b>اثر فعال</b>: {hours} ساعت و {minutes} دقیقه باقی مانده است."
        rows = []
        # Keep the scroll action alongside the sell/trade actions for this item.
        rows.append([
            InlineKeyboardButton(
                text=("⏳ طومار فعال است" if active else "📖 خواندن و فعال‌سازی طومار"),
                callback_data=("inventory:noop" if active else f"item:use_scroll:{item.id}"),
            ),
            InlineKeyboardButton(
                text="💰 فروش به فروشگاه",
                callback_data=f"item:sell:{item.id}",
            ),
        ])
        rows.append([
            InlineKeyboardButton(
                text="👤 پیشنهاد به بازیکن",
                callback_data=f"item:sell_player:{item.id}",
            )
        ])
        rows.extend([
            [InlineKeyboardButton(text="🔙 بازگشت به اسکرول‌ها", callback_data="inventory:scrolls")],
            [InlineKeyboardButton(text="🗃 بازگشت به صندوقچه", callback_data="menu:inventory")],
        ])
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    else:
        keyboard = item_details_keyboard(item.id)

    await _show(callback, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^item:use_scroll:\d+$"))
async def use_scroll_handler(callback: CallbackQuery):
    try:
        item_id = int(callback.data.rsplit(":", 1)[-1])
    except (TypeError, ValueError):
        await callback.answer("شناسهٔ اسکرول معتبر نیست.", show_alert=True)
        return

    kind = None
    item_name = ""
    async with AsyncSessionLocal() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == callback.from_user.id))
        if character is None:
            await callback.answer("قهرمان پیدا نشد.", show_alert=True)
            return
        row = (await session.execute(
            select(Inventory, Item).join(Item, Inventory.item_id == Item.id)
            .where(Inventory.character_id == character.id, Inventory.item_id == item_id, Inventory.quantity > 0, Item.item_type == "scroll")
            .with_for_update()
        )).first()
        if row is None:
            await callback.answer("این اسکرول در صندوقچه‌ات نیست.", show_alert=True)
            return
        inventory_item, item = row
        kind = scroll_kind(item.name)
        item_name = item.name
        if not kind:
            await callback.answer("اثر این اسکرول هنوز تعریف نشده است.", show_alert=True)
            return
        success, result = await activate_scroll(callback.from_user.id, kind)
        if not success:
            await callback.answer(result[:180], show_alert=True)
            return
        inventory_item.quantity -= 1
        if inventory_item.quantity <= 0:
            await session.delete(inventory_item)
        await session.commit()

    await callback.answer("اسکرول فعال شد!")
    await _show(callback, f"✨ <b>{item_name}</b> مصرف شد.\n\n{SCROLLS[kind]['description']}\n\n⏳ مدت اثر: ۲ ساعت", InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 اسکرول‌های صندوقچه", callback_data="inventory:scrolls")],
        [InlineKeyboardButton(text="🗃 بازگشت به صندوقچه", callback_data="menu:inventory")],
    ]))


# ============================================================
# Equipment Details
# ============================================================

@router.callback_query(
    F.data.regexp(r"^equipmentitem:\d+$")
)
async def equipment_details_handler(
    callback: CallbackQuery,
):
    try:
        equipment_id = int(
            callback.data.split(":")[1]
        )

    except (ValueError, IndexError):

        await callback.answer(
            "❌ شناسه تجهیزات معتبر نیست.",
            show_alert=True,
        )
        return

    success = await _render_equipment_details(
        callback,
        equipment_id,
    )

    if not success:
        await callback.answer(
            "❌ این تجهیزات در صندوقچه شما نیست.",
            show_alert=True,
        )
        return

    await callback.answer()


# ============================================================
# Equip
# ============================================================

@router.callback_query(
    F.data.regexp(r"^inventory:equip:\d+$")
)
async def inventory_equip_equipment_handler(
    callback: CallbackQuery,
):
    try:
        equipment_id = int(
            callback.data.split(":")[2]
        )

    except (ValueError, IndexError):

        await callback.answer(
            "❌ شناسه تجهیزات معتبر نیست.",
            show_alert=True,
        )
        return

    success, result_message = await equip_equipment(
        callback.from_user.id,
        equipment_id,
    )

    if not success:
        await callback.answer(
            result_message,
            show_alert=True,
        )
        return

    await _render_equipment_details(
        callback,
        equipment_id,
    )

    await callback.answer(
        "✅ تجهیزات با موفقیت مجهز شد."
    )


# ============================================================
# Unequip
# ============================================================

@router.callback_query(
    F.data.regexp(r"^inventory:unequip:\d+$")
)
async def inventory_unequip_equipment_handler(
    callback: CallbackQuery,
):
    try:
        equipment_id = int(
            callback.data.split(":")[2]
        )

    except (ValueError, IndexError):

        await callback.answer(
            "❌ شناسه تجهیزات معتبر نیست.",
            show_alert=True,
        )
        return

    success, result_message = await unequip_equipment(
        callback.from_user.id,
        equipment_id,
    )

    if not success:
        await callback.answer(
            result_message,
            show_alert=True,
        )
        return

    await _render_equipment_details(
        callback,
        equipment_id,
    )

    await callback.answer(
        "🔓 تجهیزات از حالت تجهیز خارج شد."
    )


# ============================================================
# Sell To NPC
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
            "❌ شناسه آیتم معتبر نیست.",
            show_alert=True,
        )
        return

    success, message = await sell_item(
        callback.from_user.id,
        item_id,
        1,
    )

    if not success:
        await callback.answer(
            message,
            show_alert=True,
        )
        return

    await _show(
        callback,
        message,
        inventory_keyboard(),
    )

    await callback.answer(
        "✅ فروش انجام شد."
    )


# ============================================================
# Trade - Start
# ============================================================

@router.callback_query(
    F.data.startswith("item:sell_player:")
)
async def sell_player_start_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    try:
        item_id = int(
            callback.data.split(":")[2]
        )

    except (ValueError, IndexError):

        await callback.answer(
            "❌ شناسه آیتم معتبر نیست.",
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
                "❌ شخصیت شما پیدا نشد.",
                show_alert=True,
            )
            return

        inventory = await session.scalar(
            select(Inventory).where(
                Inventory.character_id == character.id,
                Inventory.item_id == item_id,
                Inventory.quantity > 0,
            )
        )

        if inventory is None:
            await callback.answer(
                "❌ این آیتم دیگر در صندوقچه شما نیست.",
                show_alert=True,
            )
            return

        username = _normalize_username(
            callback.from_user.username
        )

        if username:
            character.telegram_username = username
            await session.commit()

    await state.clear()

    await state.update_data(
        trade_item_id=item_id,
    )

    await state.set_state(
        PlayerTrade.waiting_for_target
    )

    await callback.answer()

    if callback.message:
        await callback.message.answer(
            "👤 username تلگرام بازیکن خریدار را وارد کنید.\n\n"
            "حتماً با @ وارد کنید.\n\n"
            "مثال:\n"
            "@leaderf2f",
            reply_markup=ForceReply(
                selective=True
            ),
        )


# ============================================================
# Trade - Target Username
# ============================================================

@router.message(
    PlayerTrade.waiting_for_target
)
async def trade_target_handler(
    message: Message,
    state: FSMContext,
):
    target_text = (
        message.text or ""
    ).strip()

    if not target_text.startswith("@"):

        await message.answer(
            "❌ لطفاً username را با @ وارد کنید.\n\n"
            "مثال:\n"
            "@leaderf2f",
            reply_markup=ForceReply(
                selective=True
            ),
        )
        return

    username = _normalize_username(
        target_text
    )

    data = await state.get_data()

    item_id = data.get(
        "trade_item_id"
    )

    if not item_id:
        await state.clear()

        await message.answer(
            "❌ اطلاعات معامله پیدا نشد.\n"
            "لطفاً دوباره از صندوقچه شروع کنید."
        )
        return

    seller = await _get_character(
        message.from_user.id
    )

    if seller is None:
        await state.clear()

        await message.answer(
            "❌ شخصیت شما پیدا نشد."
        )
        return

    seller_username = _normalize_username(
        message.from_user.username
    )

    if seller_username == username:

        await message.answer(
            "❌ نمی‌توانید به خودتان معامله پیشنهاد دهید.",
            reply_markup=ForceReply(
                selective=True
            ),
        )
        return

    async with AsyncSessionLocal() as session:

        target = await session.scalar(
            select(Character).where(
                Character.telegram_username == username
            )
        )

    if target is None:

        await message.answer(
            "❌ بازیکنی با این username پیدا نشد.\n\n"
            f"🔎 جستجو: @{username}\n\n"
            "بازیکن باید حداقل یک‌بار با ربات اِلدوریا "
            "تعامل کرده باشد تا username او ثبت شود.",
            reply_markup=ForceReply(
                selective=True
            ),
        )
        return

    await state.update_data(
        target_username=username,
    )

    await state.set_state(
        PlayerTrade.waiting_for_price
    )

    await message.answer(
        "🔢 تعداد و قیمت هر عدد را به Gold وارد کنید.\n\n"
        "قالب: تعداد قیمت_هر_عدد\n"
        "مثال: 5 1300",
        reply_markup=ForceReply(
            selective=True
        ),
    )


# ============================================================
# Trade - Quantity and Unit Price
# ============================================================

@router.message(
    PlayerTrade.waiting_for_price
)
async def trade_price_handler(
    message: Message,
    state: FSMContext,
):
    # Format: quantity unit_price, e.g. 5 1300
    parts = _normalize_digits(message.text or "").replace(",", " ").replace("،", " ").split()
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        await message.answer(
            "❌ تعداد و قیمت هر عدد را با هم وارد کنید.\n\n"
            "قالب: تعداد قیمت_هر_عدد\n"
            "مثال: 5 1300",
            reply_markup=ForceReply(selective=True),
        )
        return

    quantity, unit_price = int(parts[0]), int(parts[1])
    if quantity <= 0 or unit_price <= 0:
        await message.answer(
            "❌ تعداد و قیمت هر عدد باید بیشتر از صفر باشند.\n"
            "مثال: 5 1300",
            reply_markup=ForceReply(selective=True),
        )
        return

    total_price = quantity * unit_price
    data = await state.get_data()
    item_id = data.get("trade_item_id")
    target_username = _normalize_username(data.get("target_username"))

    if not item_id or not target_username:
        await state.clear()
        await message.answer(
            "❌ اطلاعات معامله پیدا نشد.\nلطفاً دوباره از صندوقچه شروع کنید."
        )
        return

    seller_telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        seller = await session.scalar(
            select(Character).where(
                Character.telegram_id == seller_telegram_id
            ).with_for_update()
        )
        if seller is None:
            await state.clear()
            await message.answer("❌ شخصیت شما پیدا نشد.")
            return

        seller_username = _normalize_username(message.from_user.username)
        if seller_username:
            seller.telegram_username = seller_username

        target = await session.scalar(
            select(Character).where(Character.telegram_username == target_username)
        )
        if target is None:
            await message.answer(
                "❌ بازیکنی با این username پیدا نشد.\n\n"
                f"🔎 جستجو: @{target_username}",
                reply_markup=ForceReply(selective=True),
            )
            return

        if target.telegram_id == seller_telegram_id:
            await state.clear()
            await message.answer("❌ نمی‌توانید به خودتان معامله پیشنهاد دهید.")
            return

        row = (await session.execute(
            select(Inventory, Item)
            .join(Item, Inventory.item_id == Item.id)
            .where(
                Inventory.character_id == seller.id,
                Inventory.item_id == item_id,
                Inventory.quantity > 0,
            )
            .with_for_update()
        )).first()

        if row is None:
            await state.clear()
            await message.answer("❌ این آیتم دیگر در صندوقچه شما نیست.")
            return

        inventory_item, item = row
        if quantity > inventory_item.quantity:
            await message.answer(
                "❌ تعداد درخواستی بیشتر از موجودی شماست.\n"
                f"📦 موجودی فعلی: {inventory_item.quantity}\n"
                "تعداد و قیمت هر عدد را دوباره بفرستید؛ مثال: 5 1300",
                reply_markup=ForceReply(selective=True),
            )
            return

        existing_trade = await session.scalar(
            select(Trade).where(
                Trade.seller_telegram_id == seller_telegram_id,
                Trade.buyer_telegram_id == target.telegram_id,
                Trade.item_id == item.id,
                Trade.status == "pending",
            )
        )
        if existing_trade is not None:
            await state.clear()
            await message.answer(
                "⚠️ برای این بازیکن، همین آیتم یک پیشنهاد معامله فعال دارد."
            )
            return

        trade = Trade(
            seller_telegram_id=seller_telegram_id,
            buyer_telegram_id=target.telegram_id,
            item_id=item.id,
            quantity=quantity,
            # Trade.price stores the total amount for the entire stack.
            price=total_price,
            status="pending",
        )
        session.add(trade)
        await session.flush()

        item_name = item.name
        seller_name = seller.name
        target_telegram_id = target.telegram_id
        await session.commit()
        trade_id = trade.id

    await state.clear()

    seller_message = await message.answer(
        "✅ پیشنهاد معامله ایجاد شد.\n\n"
        f"👤 خریدار: @{target_username}\n"
        f"🗃 آیتم: {item_name}\n"
        f"🔢 تعداد: {quantity}\n"
        f"💰 قیمت هر عدد: {unit_price:,} Gold\n"
        f"💳 مبلغ کل: {total_price:,} Gold\n\n"
        "⏳ منتظر پاسخ خریدار..."
    )

    try:
        buyer_message = await bot.send_message(
            chat_id=target_telegram_id,
            text=(
                "📨 پیشنهاد معامله جدید!\n\n"
                f"👤 فروشنده: {seller_name}\n"
                f"🗃 آیتم: {item_name}\n"
                f"🔢 تعداد: {quantity}\n"
                f"💰 قیمت هر عدد: {unit_price:,} Gold\n"
                f"💳 مبلغ کل: {total_price:,} Gold"
            ),
            reply_markup=trade_request_keyboard(trade_id),
        )
    except Exception:
        await message.answer(
            "⚠️ معامله ساخته شد، اما ارسال پیام به خریدار موفق نبود.\n\n"
            "ممکن است خریدار هنوز ربات را Start نکرده باشد."
        )
        return

    async with AsyncSessionLocal() as session:
        trade = await session.get(Trade, trade_id)
        if trade is not None:
            trade.seller_message_id = seller_message.message_id
            trade.seller_chat_id = message.chat.id
            trade.buyer_message_id = buyer_message.message_id
            trade.buyer_chat_id = target_telegram_id
            await session.commit()


# ============================================================
# Trade - Accept
# ============================================================

@router.callback_query(
    F.data.startswith("trade:accept:")
)
async def trade_accept_handler(
    callback: CallbackQuery,
):
    try:

        trade_id = int(
            callback.data.split(":")[2]
        )

    except (ValueError, IndexError):

        await callback.answer(
            "❌ شناسه معامله معتبر نیست.",
            show_alert=True,
        )
        return

    buyer_telegram_id = (
        callback.from_user.id
    )

    async with AsyncSessionLocal() as session:

        trade = await session.scalar(
            select(Trade)
            .where(
                Trade.id == trade_id
            )
            .with_for_update()
        )

        if trade is None:

            await callback.answer(
                "❌ این معامله پیدا نشد.",
                show_alert=True,
            )
            return

        if trade.status != "pending":

            await callback.answer(
                "⚠️ این معامله دیگر فعال نیست.",
                show_alert=True,
            )
            return

        if trade.buyer_telegram_id != buyer_telegram_id:

            await callback.answer(
                "⛔ این پیشنهاد معامله برای شما نیست.",
                show_alert=True,
            )
            return

        buyer = await session.scalar(
            select(Character).where(
                Character.telegram_id == buyer_telegram_id
            )
        )

        if buyer is None:

            await callback.answer(
                "❌ شخصیت شما پیدا نشد.",
                show_alert=True,
            )
            return

        seller = await session.scalar(
            select(Character).where(
                Character.telegram_id == trade.seller_telegram_id
            )
        )

        if seller is None:

            trade.status = "rejected"

            await session.commit()

            await callback.answer(
                "❌ فروشنده دیگر وجود ندارد.",
                show_alert=True,
            )
            return

        inventory = await session.scalar(
            select(Inventory)
            .where(
                Inventory.character_id == seller.id,
                Inventory.item_id == trade.item_id,
                Inventory.quantity >= trade.quantity,
            )
            .with_for_update()
        )

        if inventory is None:

            trade.status = "rejected"

            await session.commit()

            await callback.answer(
                "❌ فروشنده دیگر این آیتم را ندارد.",
                show_alert=True,
            )
            return

        if buyer.gold < trade.price:

            await callback.answer(
                "💰 طلای کافی برای این معامله ندارید.",
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

        if buyer_inventory is None:

            buyer_inventory = Inventory(
                character_id=buyer.id,
                item_id=trade.item_id,
                quantity=0,
            )

            session.add(
                buyer_inventory
            )

            await session.flush()

        inventory.quantity -= (
            trade.quantity
        )

        if inventory.quantity < 0:
            inventory.quantity = 0

        buyer_inventory.quantity += (
            trade.quantity
        )

        buyer.gold -= trade.price
        seller.gold += trade.price

        trade.status = "accepted"

        item = await session.get(
            Item,
            trade.item_id,
        )

        item_name = (
            item.name
            if item is not None
            else "آیتم"
        )

        price = trade.price
        quantity = trade.quantity
        unit_price = price // quantity if quantity else price

        seller_message_id = (
            trade.seller_message_id
        )

        seller_chat_id = (
            trade.seller_chat_id
        )

        await session.commit()

    # ========================================================
    # Buyer Message
    # ========================================================

    try:

        await callback.message.edit_text(
            (
                "✅ معامله با موفقیت انجام شد!\n\n"
                f"🗃 آیتم: {item_name}\n"
                f"🔢 تعداد: {quantity}\n"
                f"💰 قیمت هر عدد: {unit_price:,} Gold\n"
                f"💳 مبلغ پرداخت‌شده: {price:,} Gold\n\n"
                "🎉 آیتم به صندوقچه شما منتقل شد."
            ),
            reply_markup=None,
        )

    except Exception:
        pass

    # ========================================================
    # Seller Message
    # ========================================================

    if seller_chat_id and seller_message_id:

        try:

            await bot.edit_message_text(
                chat_id=seller_chat_id,
                message_id=seller_message_id,
                text=(
                    "✅ معامله با موفقیت انجام شد!\n\n"
                    f"🗃 آیتم: {item_name}\n"
                    f"🔢 تعداد: {quantity}\n"
                    f"💰 قیمت هر عدد: {unit_price:,} Gold\n"
                    f"💳 مبلغ دریافتی: {price:,} Gold\n\n"
                    "🎉 آیتم با موفقیت به خریدار منتقل شد."
                ),
                reply_markup=None,
            )

        except Exception:
            pass

    await callback.answer(
        "✅ معامله با موفقیت انجام شد."
    )


# ============================================================
# Trade - Reject
# ============================================================

@router.callback_query(
    F.data.startswith("trade:reject:")
)
async def trade_reject_handler(
    callback: CallbackQuery,
):
    try:

        trade_id = int(
            callback.data.split(":")[2]
        )

    except (ValueError, IndexError):

        await callback.answer(
            "❌ شناسه معامله معتبر نیست.",
            show_alert=True,
        )
        return

    buyer_telegram_id = (
        callback.from_user.id
    )

    async with AsyncSessionLocal() as session:

        trade = await session.scalar(
            select(Trade)
            .where(
                Trade.id == trade_id
            )
            .with_for_update()
        )

        if trade is None:

            await callback.answer(
                "❌ این معامله پیدا نشد.",
                show_alert=True,
            )
            return

        if trade.status != "pending":

            await callback.answer(
                "⚠️ این معامله دیگر فعال نیست.",
                show_alert=True,
            )
            return

        if trade.buyer_telegram_id != buyer_telegram_id:

            await callback.answer(
                "⛔ این پیشنهاد معامله برای شما نیست.",
                show_alert=True,
            )
            return

        trade.status = "rejected"

        item = await session.get(
            Item,
            trade.item_id,
        )

        item_name = (
            item.name
            if item is not None
            else "آیتم"
        )

        seller_chat_id = (
            trade.seller_chat_id
        )

        seller_message_id = (
            trade.seller_message_id
        )
        quantity = trade.quantity

        await session.commit()

    # ========================================================
    # Buyer Message
    # ========================================================

    try:

        await callback.message.edit_text(
            (
                "❌ معامله رد شد.\n\n"
                f"🗃 آیتم: {item_name}\n"
                f"🔢 تعداد: {quantity}\n\n"
                "این پیشنهاد دیگر فعال نیست."
            ),
            reply_markup=None,
        )

    except Exception:
        pass

    # ========================================================
    # Seller Message
    # ========================================================

    if seller_chat_id and seller_message_id:

        try:

            await bot.edit_message_text(
                chat_id=seller_chat_id,
                message_id=seller_message_id,
                text=(
                    "❌ پیشنهاد معامله رد شد.\n\n"
                    f"🗃 آیتم: {item_name}\n"
                    f"🔢 تعداد: {quantity}\n\n"
                    "خریدار این پیشنهاد را رد کرد."
                ),
                reply_markup=None,
            )

        except Exception:
            pass

    await callback.answer(
        "❌ معامله رد شد."
    )