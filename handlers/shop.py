import html
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.shop import (
    shop_equipment_details_keyboard,
    shop_equipment_keyboard,
    shop_item_details_keyboard,
    shop_items_keyboard,
    shop_main_keyboard,
)

from keyboards.main_menu import main_menu_keyboard

from services.shop_service import (
    buy_equipment,
    buy_item,
    get_shop_equipment,
    get_shop_equipment_item,
    get_shop_item,
    get_shop_items,
)

from services.panel_image_service import show_panel


router = Router()


ITEM_TYPE_TITLES = {
    "potion": "🧪 معجون‌ها",
    "material": "🗃 متریال",
    "scroll": "📜 اسکرول‌ها",
}


RARITY_NAMES = {
    "common": "⚪ معمولی",
    "uncommon": "🟢 غیرمعمولی",
    "rare": "🔵 کمیاب",
    "epic": "🟣 حماسی",
    "legendary": "🟠 افسانه‌ای",
    "mythic": "🔴 اسطوره‌ای",
    "divine": "✨ الهی",
}




async def _show_shop_category_panel(callback, text, reply_markup):
    """Send a fresh shop panel; do not delete or edit the previous message."""
    return await show_panel(
        callback=callback,
        panel_name="shop",
        text=text,
        reply_markup=reply_markup,
    )


async def _ensure_divine_eldoria_set() -> None:
    """Ensure a full endgame divine set exists in the gem shop. Idempotent."""
    from sqlalchemy import select
    from database.database import AsyncSessionLocal
    from models.equipment import Equipment

    # Values are base values. The central stat service multiplies divine gear
    # by 350, so the sword alone grants 50,750 ATK (145 x 350).
    pieces = [
        dict(name="شمشیر آسمانی اِلدوریا", equipment_type="weapon", attack=145, magic_power=110, defense=35, magic_defense=35, hp=0, mana=0, speed=20, accuracy=25, critical=12, gem_price=100, description="سلاح نهایی اِلدوریا؛ بیش از ۵۰ هزار ATK پس از اعمال ضریب کمیابی الهی."),
        dict(name="تاج الهی اِلدوریا", equipment_type="helmet", attack=25, magic_power=35, defense=80, magic_defense=90, hp=300, mana=350, speed=10, accuracy=15, critical=5, gem_price=75, description="تاج ست الهی؛ افزایش چشمگیر بقا و مقاومت جادویی."),
        dict(name="زره الهی اِلدوریا", equipment_type="armor", attack=30, magic_power=20, defense=220, magic_defense=180, hp=1200, mana=250, speed=0, accuracy=5, critical=0, gem_price=125, description="زره نهایی برای ایستادگی در برابر باس‌های سطح ۲۰۰."),
        dict(name="چکمه‌های الهی اِلدوریا", equipment_type="boots", attack=20, magic_power=20, defense=50, magic_defense=55, hp=200, mana=150, speed=35, accuracy=20, critical=4, gem_price=65, description="چکمه‌های سبک با سرعت، دقت و دفاع الهی."),
        dict(name="حلقهٔ الهی اِلدوریا", equipment_type="ring", attack=30, magic_power=45, defense=60, magic_defense=75, hp=250, mana=300, speed=15, accuracy=20, critical=10, gem_price=85, description="حلقهٔ باستانی برای تقویت حمله و جادو."),
        dict(name="گردنبند الهی اِلدوریا", equipment_type="necklace", attack=25, magic_power=50, defense=90, magic_defense=100, hp=400, mana=450, speed=10, accuracy=15, critical=8, gem_price=90, description="گردنبند محافظ با افزایش بزرگ HP و Mana."),
    ]
    async with AsyncSessionLocal() as session:
        for piece in pieces:
            item = await session.scalar(select(Equipment).where(Equipment.name == piece["name"]))
            if item is None:
                item = Equipment(
                    name=piece["name"], description=piece["description"], set_key="divine_eldoria",
                    equipment_type=piece["equipment_type"], rarity="divine", required_level=100,
                    shop_price=0, gem_price=piece["gem_price"], is_active=True,
                    attack=piece["attack"], magic_power=piece["magic_power"], defense=piece["defense"],
                    magic_defense=piece["magic_defense"], hp=piece["hp"], mana=piece["mana"],
                    speed=piece["speed"], accuracy=piece["accuracy"], critical=piece["critical"],
                )
                session.add(item)
            else:
                # Correct outdated divine sword and keep the complete set consistent.
                item.description = piece["description"]
                item.set_key = "divine_eldoria"
                item.equipment_type = piece["equipment_type"]
                item.rarity = "divine"
                item.required_level = 100
                item.shop_price = 0
                item.gem_price = piece["gem_price"]
                item.is_active = True
                for stat in ("attack", "magic_power", "defense", "magic_defense", "hp", "mana", "speed", "accuracy", "critical"):
                    setattr(item, stat, piece[stat])
        await session.commit()


def rarity_name(
    rarity: str,
) -> str:
    return RARITY_NAMES.get(
        rarity,
        rarity,
    )


# ============================================================
# Shop Main
# ============================================================

@router.callback_query(
    F.data == "menu:shop"
)
async def shop_handler(
    callback: CallbackQuery,
):
    text = (
        "🏪 <b>فروشگاه اِلدوریا</b>\n\n"
        "هر چیزی که برای ادامه ماجراجویی نیاز داری اینجاست.\n"
        "دسته‌بندی موردنظر را انتخاب کن:"
    )

    await show_panel(
        callback=callback,
        panel_name="shop",
        text=text,
        reply_markup=shop_main_keyboard(),
    )

    await callback.answer()


# ============================================================
# Item Categories
# ============================================================

@router.callback_query(
    F.data.in_({
        "shop:potion",
        "shop:material",
        "shop:scroll",
    })
)
async def shop_item_category_handler(
    callback: CallbackQuery,
):
    item_type = callback.data.split(":")[1]

    items = await get_shop_items(
        item_type
    )

    title = ITEM_TYPE_TITLES[
        item_type
    ]

    if not items:
        text = (
            f"{title}\n\n"
            "🗃 فعلاً آیتمی در این بخش "
            "برای فروش قرار نگرفته است."
        )

        await show_panel(
            callback=callback,
            panel_name="shop",
            text=text,
            reply_markup=shop_main_keyboard(),
        )

        await callback.answer()
        return

    text = (
        f"{title}\n\n"
        "برای دیدن جزئیات و خرید، "
        "آیتم موردنظر را انتخاب کن."
    )

    await show_panel(
        callback=callback,
        panel_name="shop",
        text=text,
        reply_markup=shop_items_keyboard(
            items,
            item_type,
        ),
    )

    await callback.answer()


# ============================================================
# Shop Item List Back
# ============================================================

@router.callback_query(
    F.data == "shop:itemlist"
)
async def shop_itemlist_handler(
    callback: CallbackQuery,
):
    text = (
        "🏪 <b>فروشگاه اِلدوریا</b>\n\n"
        "دسته‌بندی موردنظر را انتخاب کن:"
    )

    await show_panel(
        callback=callback,
        panel_name="shop",
        text=text,
        reply_markup=shop_main_keyboard(),
    )

    await callback.answer()


# ============================================================
# Item Details
# ============================================================

@router.callback_query(
    F.data.startswith("shop:item:")
)
async def shop_item_details_handler(
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

    item = await get_shop_item(
        item_id
    )

    if item is None:
        await callback.answer(
            "❌ این آیتم دیگر در فروشگاه موجود نیست.",
            show_alert=True,
        )
        return

    text = (
        f"{item.name}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 کمیابی: "
        f"{rarity_name(item.rarity)}\n"
        f"🗃 نوع: "
        f"{ITEM_TYPE_TITLES.get(item.item_type, item.item_type)}\n"
        f"💰 قیمت خرید: "
        f"{item.buy_price:,} Gold\n"
        f"💰 قیمت فروش: "
        f"{item.sell_price:,} Gold\n\n"
        f"📝 {item.description or 'بدون توضیحات'}"
    )

    await show_panel(
        callback=callback,
        panel_name="shop",
        text=text,
        reply_markup=shop_item_details_keyboard(
            item.id
        ),
    )

    await callback.answer()


# ============================================================
# Buy Item
# ============================================================

@router.callback_query(F.data.startswith("shop:buyqty:"))
async def shop_buy_quantity_confirm(callback: CallbackQuery):
    try:
        _, _, item_id_text, qty_text = (callback.data or "").split(":", 3)
        item_id, quantity = int(item_id_text), int(qty_text)
    except (ValueError, TypeError):
        await callback.answer("❌ تعداد یا آیتم نامعتبر است.", show_alert=True); return
    if quantity not in {1, 5, 10, 15, 20}:
        await callback.answer("❌ تعداد خرید مجاز نیست.", show_alert=True); return
    item = await get_shop_item(item_id)
    if item is None:
        await callback.answer("❌ این آیتم دیگر در فروشگاه موجود نیست.", show_alert=True); return
    total = int(item.buy_price) * quantity
    from sqlalchemy import select
    from database.database import AsyncSessionLocal
    from models.character import Character
    async with AsyncSessionLocal() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == callback.from_user.id))
        if character is None:
            await callback.answer("ابتدا شخصیت بساز.", show_alert=True); return
        balance = int(character.gold or 0)
    text = (f"🧾 <b>تأیید خرید</b>\n\n{html.escape(item.name)}\n📦 تعداد: ×{quantity}\n"
            f"💰 قیمت هر عدد: {item.buy_price:,} Gold\n💰 هزینه نهایی: <b>{total:,} Gold</b>\n"
            f"👛 موجودی فعلی: {balance:,} Gold\n👛 پس از خرید: {balance-total:,} Gold\n\nآیا خرید را تأیید می‌کنی؟")
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ تأیید خرید", callback_data=f"shop:confirmbuy:{item_id}:{quantity}")], [InlineKeyboardButton(text="❌ لغو", callback_data=f"shop:item:{item_id}")]])
    await show_panel(callback=callback, panel_name="shop", text=text, parse_mode="HTML", reply_markup=markup)
    await callback.answer()

@router.callback_query(F.data.startswith("shop:confirmbuy:"))
async def shop_buy_quantity_execute(callback: CallbackQuery):
    try:
        _, _, item_id_text, qty_text = (callback.data or "").split(":", 3)
        item_id, quantity = int(item_id_text), int(qty_text)
    except (ValueError, TypeError):
        await callback.answer("❌ تعداد یا آیتم نامعتبر است.", show_alert=True); return
    if quantity not in {1, 5, 10, 15, 20}:
        await callback.answer("❌ تعداد خرید مجاز نیست.", show_alert=True); return
    success, result = await buy_item(callback.from_user.id, item_id, quantity)
    await callback.answer(result[:180], show_alert=True)
    if not success: return
    item = await get_shop_item(item_id)
    if item is None:
        await show_panel(callback=callback, panel_name="shop", text=result, reply_markup=shop_main_keyboard()); return
    text = f"✅ <b>خرید انجام شد</b>\n\n{html.escape(item.name)}\n📦 تعداد: ×{quantity}\n💰 هزینه پرداخت‌شده: {item.buy_price*quantity:,} Gold\n\nآیتم‌ها به صندوقچه اضافه شدند."
    await show_panel(callback=callback, panel_name="shop", text=text, reply_markup=shop_item_details_keyboard(item.id))

@router.callback_query(
    F.data.startswith("shop:buy:")
)
async def shop_buy_item_handler(
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

    success, message = await buy_item(
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

    item = await get_shop_item(
        item_id
    )

    if item is None:
        await show_panel(
            callback=callback,
            panel_name="shop",
            text="🏪 خرید با موفقیت انجام شد.",
            reply_markup=shop_main_keyboard(),
        )
        return

    text = (
        f"{item.name}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 کمیابی: "
        f"{rarity_name(item.rarity)}\n"
        f"🗃 نوع: "
        f"{ITEM_TYPE_TITLES.get(item.item_type, item.item_type)}\n"
        f"💰 قیمت خرید: "
        f"{item.buy_price:,} Gold\n\n"
        "✅ این آیتم با موفقیت "
        "به صندوقچه اضافه شد."
    )

    await show_panel(
        callback=callback,
        panel_name="shop",
        text=text,
        reply_markup=shop_item_details_keyboard(
            item.id
        ),
    )


# ============================================================
# Equipment Shop
# ============================================================

# Catalog is explicit: legacy equipment remains owned but is not silently repriced.
SHOP_TIERS = {"gold": ("آهنی", "فولادی", "کریستالی"), "gem": ("اهریمنی", "الهی", "اِلدوریایی")}
SHOP_SLOTS = {"weapon": "⚔️ سلاح", "armor": "🛡️ زره", "helmet": "🪖 کلاه", "boots": "👢 کفش", "ring": "💍 انگشتر", "necklace": "📿 گردنبند"}


def _catalog_keyboard(currency: str, tier: str | None = None, slot: str | None = None, items=()):
    rows = []
    if tier is None:
        rows = [[InlineKeyboardButton(text=t, callback_data=f"shop:catalog:{currency}:{i}")] for i,t in enumerate(SHOP_TIERS[currency])]
    elif slot is None:
        rows = [[InlineKeyboardButton(text=label, callback_data=f"shop:catalog:{currency}:{SHOP_TIERS[currency].index(tier)}:{key}")] for key,label in SHOP_SLOTS.items()]
    else:
        for item in items:
            price = item.shop_price if currency == "gold" else item.gem_price
            cb = f"shop:equipment_item:{item.id}" if currency == "gold" else f"shop:gembuy:{item.id}"
            rows.append([InlineKeyboardButton(text=f"{item.name} — {price:,} {'💰' if currency == 'gold' else '💎'}", callback_data=cb)])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data=(f"shop:catalog:{currency}:{SHOP_TIERS[currency].index(tier)}" if slot else f"shop:catalog:{currency}" if tier else "menu:shop"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "shop:equipment")
async def shop_equipment_handler(callback: CallbackQuery):
    await _show_shop_category_panel(callback, "⚔️ <b>آرشیو تجهیزات Gold</b>\n✦ رده موردنظر را انتخاب کن.\n💰 بازه قیمت: 1,000 تا 15,000 Gold", _catalog_keyboard("gold"))
    await callback.answer()


@router.callback_query(F.data.startswith("shop:catalog:"))
async def shop_catalog_handler(callback: CallbackQuery):
    from sqlalchemy import select
    from database.database import AsyncSessionLocal
    from models.equipment import Equipment
    parts = (callback.data or "").split(":")
    if len(parts) not in (3, 4, 5) or parts[2] not in SHOP_TIERS:
        await callback.answer("دسته نامعتبر است.", show_alert=True); return
    currency = parts[2]
    tier = None
    slot = None
    if len(parts) >= 4:
        try: tier = SHOP_TIERS[currency][int(parts[3])]
        except (ValueError, IndexError):
            await callback.answer("رده نامعتبر است.", show_alert=True); return
    if len(parts) == 5:
        slot = parts[4]
        if slot not in SHOP_SLOTS:
            await callback.answer("بخش نامعتبر است.", show_alert=True); return
    items = []
    if slot:
        async with AsyncSessionLocal() as session:
            price_field = Equipment.shop_price if currency == "gold" else Equipment.gem_price
            items = list((await session.scalars(select(Equipment).where(
                Equipment.is_active.is_(True), Equipment.equipment_type == slot,
                Equipment.name.like(f"{tier} %"), price_field > 0,
            ).order_by(price_field, Equipment.id))).all())
    title = f"{'💰' if currency == 'gold' else '💎'} <b>آرشیو تجهیزات اِلدوریا</b>"
    detail = f"\n✦ {html.escape(tier)}" if tier else "\n✦ رده تجهیزات را انتخاب کن"
    detail += f" / {SHOP_SLOTS[slot]}" if slot else ""
    if slot and not items: detail += "\nهنوز آیتمی در این بخش ثبت نشده؛ ابتدا همگام‌سازی کاتالوگ را اجرا کن."
    await _show_shop_category_panel(callback, title + detail, _catalog_keyboard(currency,tier,slot,items))
    await callback.answer()


# ============================================================
# Equipment Details
# ============================================================

@router.callback_query(
    F.data.startswith("shop:equipment_item:")
)
async def shop_equipment_details_handler(
    callback: CallbackQuery,
):
    try:
        equipment_id = int(callback.data.rsplit(":", 1)[-1])

    except (ValueError, IndexError):
        await callback.answer(
            "❌ تجهیز نامعتبر است.",
            show_alert=True,
        )
        return

    equipment = await get_shop_equipment_item(
        equipment_id
    )

    if equipment is None:
        await callback.answer(
            "❌ این تجهیز دیگر در فروشگاه موجود نیست.",
            show_alert=True,
        )
        return

    from services.equipment_service import (
        get_character,
        get_character_equipment,
    )

    character = await get_character(
        callback.from_user.id
    )

    if character is None:
        await callback.answer(
            "❌ قهرمان پیدا نشد.",
            show_alert=True,
        )
        return

    owned = await get_character_equipment(
        callback.from_user.id,
        equipment.id,
    )

    level_ok = (
        character.level
        >= equipment.required_level
    )

    already_owned = (
        owned is not None
        and owned.quantity > 0
    )

    can_buy = (
        level_ok
        and not already_owned
    )

    status_lines = []

    if already_owned:
        status_lines.append(
            "⚠️ این تجهیز را قبلاً داری."
        )

    elif not level_ok:
        status_lines.append(
            f"🔒 سطح موردنیاز: "
            f"{equipment.required_level}"
        )

    else:
        status_lines.append(
            "🟢 آماده خرید"
        )

    rarity = str(equipment.rarity or "common").lower()
    rarity_multiplier = {
        "common": 1, "uncommon": 3, "rare": 10, "epic": 30,
        "legendary": 80, "mythic": 180, "divine": 350,
    }.get(rarity, 1)
    utility_multiplier = {
        "common": 1.0, "uncommon": 1.1, "rare": 1.25, "epic": 1.5,
        "legendary": 2.0, "mythic": 2.5, "divine": 3.0,
    }.get(rarity, 1.0)
    text = (
        f"{equipment.name}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🗃 نوع: {equipment.equipment_type}\n"
        f"💎 کمیابی: {rarity_name(equipment.rarity)}\n"
        f"⭐ سطح موردنیاز: {equipment.required_level}\n"
        f"💰 قیمت: {equipment.shop_price:,} Gold\n\n"
        "📊 ویژگی‌های نهایی (با ضریب کمیابی):\n"
        f"⚔️ Attack: +{int(equipment.attack) * rarity_multiplier:,}\n"
        f"🔮 Magic Power: +{int(equipment.magic_power) * rarity_multiplier:,}\n"
        f"🛡️ Defense: +{int(equipment.defense) * rarity_multiplier:,}\n"
        f"🔰 Magic Defense: +{int(equipment.magic_defense) * rarity_multiplier:,}\n"
        f"❤️ HP: +{int(equipment.hp) * rarity_multiplier:,}\n"
        f"💧 Mana: +{int(equipment.mana) * rarity_multiplier:,}\n"
        f"💨 Speed: +{int(equipment.speed * utility_multiplier):,}\n"
        f"🎯 Accuracy: +{int(equipment.accuracy * utility_multiplier):,}\n"
        f"💥 Critical: +{int(equipment.critical * utility_multiplier)}%\n\n"
        f"📝 {equipment.description or 'بدون توضیحات'}\n\n"
        + "\n".join(status_lines)
    )

    await show_panel(
        callback=callback,
        panel_name="shop",
        text=text,
        reply_markup=shop_equipment_details_keyboard(
            equipment.id,
            can_buy,
        ),
    )

    await callback.answer()


# ============================================================
# Buy Equipment
# ============================================================

@router.callback_query(
    F.data.startswith("shop:buy_equipment:")
)
async def shop_buy_equipment_handler(
    callback: CallbackQuery,
):
    try:
        equipment_id = int(callback.data.rsplit(":", 1)[-1])

    except (ValueError, IndexError):
        await callback.answer(
            "❌ تجهیز نامعتبر است.",
            show_alert=True,
        )
        return

    success, message = await buy_equipment(
        callback.from_user.id,
        equipment_id,
    )

    await callback.answer(
        message,
        show_alert=True,
    )

    if not success:
        return

    equipment = await get_shop_equipment_item(
        equipment_id
    )

    if equipment is None:
        await show_panel(
            callback=callback,
            panel_name="shop",
            text="🏪 خرید با موفقیت انجام شد.",
            reply_markup=shop_main_keyboard(),
        )
        return

    text = (
        f"{equipment.name}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✅ تجهیز با موفقیت به صندوقچه "
        "تجهیزات اضافه شد.\n\n"
        f"💰 قیمت پرداخت‌شده: "
        f"{equipment.shop_price:,} Gold"
    )

    await show_panel(
        callback=callback,
        panel_name="shop",
        text=text,
        reply_markup=shop_equipment_details_keyboard(
            equipment.id,
            False,
        ),
    )


# ============================================================
# Back to Main Menu
# ============================================================

@router.callback_query(
    F.data == "shop:back"
)
async def shop_back_handler(
    callback: CallbackQuery,
):
    text = (
        "🎮 <b>منوی اصلی World Eldoria</b>\n\n"
        "🌌 ماجراجویی تو در اِلدوریا ادامه دارد..."
    )

    await show_panel(
        callback=callback,
        panel_name="main_menu",
        text=text,
        reply_markup=main_menu_keyboard(),
    )

    await callback.answer()

@router.callback_query(F.data == "shop:gems")
async def gem_shop_handler(callback: CallbackQuery):
    await _show_shop_category_panel(callback, "💎 <b>آرشیو تجهیزات Gems</b>\n✦ رده موردنظر را انتخاب کن.\n💎 بازه قیمت: 300 تا 1,500 Gems", _catalog_keyboard("gem"))
    await callback.answer()

@router.callback_query(F.data.startswith("shop:gembuy:"))
async def gem_shop_buy_handler(callback: CallbackQuery):
    from sqlalchemy import select
    from database.database import AsyncSessionLocal
    from models.character import Character
    from models.equipment import Equipment, CharacterEquipment
    try:
        equipment_id = int((callback.data or "").rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer("شناسهٔ تجهیز نامعتبر است.", show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == callback.from_user.id).with_for_update()
        )
        item = await session.scalar(select(Equipment).where(
            Equipment.id == equipment_id, Equipment.is_active.is_(True), Equipment.gem_price > 0
        ))
        if character is None or item is None:
            ok, msg = False, "قهرمان یا تجهیز پیدا نشد."
        elif character.level < item.required_level:
            ok, msg = False, f"برای خرید این تجهیز باید حداقل سطح {item.required_level} باشی."
        elif character.gems < item.gem_price:
            ok, msg = False, "جم کافی نداری؛ می‌توانی از منوی اصلی گلد را به جم تبدیل کنی."
        else:
            existing = await session.scalar(select(CharacterEquipment.id).where(
                CharacterEquipment.character_id == character.id,
                CharacterEquipment.equipment_id == item.id,
                CharacterEquipment.quantity > 0,
            ).with_for_update())
            if existing:
                ok, msg = False, "این تجهیز را قبلاً داری."
            else:
                character.gems -= item.gem_price
                session.add(CharacterEquipment(
                    character_id=character.id, equipment_id=item.id, quantity=1, equipped=False
                ))
                await session.commit()
                ok, msg = True, f"تجهیز «{item.name}» با موفقیت خریداری شد."
    await callback.answer(msg, show_alert=not ok)
    if ok:
        await gem_shop_handler(callback)


@router.message(Command("shop"))
async def shop_command(message: Message):
    from services.panel_image_service import send_panel
    await send_panel(message, "shop", "🏪 <b>فروشگاه اِلدوریا</b>\n\nدسته‌بندی موردنظر را انتخاب کن:", shop_main_keyboard())
