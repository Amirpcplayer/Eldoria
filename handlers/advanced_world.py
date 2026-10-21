from __future__ import annotations
import html
from datetime import datetime
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from database.database import AsyncSessionLocal
from models.character import Character
from models.equipment import Equipment, CharacterEquipment
from models.item import Item
from models.inventory import Inventory
from models.social_systems import Pet, CharacterPet
from models.world_systems import WorldBossContribution, WorldBoss, PvpRating
from services.panel_image_service import show_panel
from services.world_progression_service import (list_market_page, get_bestiary, ensure_world_boss, attack_world_boss, buy_market_listing, create_market_listing, create_equipment_market_listing, evolve_active_pet, upgrade_equipment, get_notifications, mark_notifications_read, cancel_market_listing, get_owned_market_listings, get_inventory_item_ids, get_inventory_equipment_ids, update_market_listing_price)
from services.social_service import active_pets, activate_pet
router=Router(name='advanced_world')

class MarketSellStates(StatesGroup):
    waiting_quantity_price = State()
    waiting_edit_price = State()

async def panel(cb:CallbackQuery,text:str,kb:InlineKeyboardMarkup,panel_name:str='main_menu'):
    await show_panel(callback=cb,panel_name=panel_name,text=text,reply_markup=kb,parse_mode='HTML')
    try: await cb.answer()
    except Exception: pass

def back_row(data='menu:back'):
    return [InlineKeyboardButton(text='🔙 بازگشت',callback_data=data)]



@router.callback_query(F.data=='menu:pvp_league')
async def pvp_league_menu(cb:CallbackQuery):
    async with AsyncSessionLocal() as s:
        rows=(await s.execute(select(PvpRating,Character).join(Character,Character.id==PvpRating.character_id).order_by(PvpRating.rating.desc(),PvpRating.wins.desc()).limit(10))).all()
    lines=['🏆 <b>لیگ PvP اِلدوریا</b>','پیروزی: +۲۰ امتیاز · شکست: −۱۰ امتیاز (حداقل صفر)','']
    if not rows: lines.append('هنوز رتبه‌ای ثبت نشده؛ اولین مبارزهٔ PvP را انجام بده.')
    for i,(rating,char) in enumerate(rows,1):
        medal={1:'🥇',2:'🥈',3:'🥉'}.get(i,'🔹')
        handle=f'@{char.telegram_username}' if char.telegram_username else f'ID {char.telegram_id}'
        lines.append(f"{medal} <b>{i}. {html.escape(char.name)}</b> · Lv.{char.level} · {rating.rating} امتیاز\n{html.escape(handle)} · برد {rating.wins} / باخت {rating.losses}")
    await panel(cb,'\n'.join(lines),InlineKeyboardMarkup(inline_keyboard=[back_row('menu:pvp')]))

@router.callback_query(F.data=='menu:notifications')
async def notifications_menu(cb:CallbackQuery):
    rows=await get_notifications(cb.from_user.id)
    unread=sum(1 for r in rows if not r.delivered)
    lines=[f'🔔 <b>اعلان‌های قهرمان</b> · خوانده‌نشده: {unread}','']
    if not rows: lines.append('اعلانی ثبت نشده است.')
    for r in rows:
        mark='🆕' if not r.delivered else '✓'
        lines.append(f"{mark} <code>{r.created_at:%m-%d %H:%M}</code> · {html.escape(r.message)}")
    await mark_notifications_read(cb.from_user.id)
    await panel(cb,'\n'.join(lines),InlineKeyboardMarkup(inline_keyboard=[back_row()]))

@router.callback_query(F.data=='menu:bestiary')
async def bestiary_menu(cb:CallbackQuery):
    rows=await get_bestiary(cb.from_user.id)
    lines=['📖 <b>دفترچهٔ هیولاها</b>','هر دشمنی که شکست بدهی در دفترچه ثبت می‌شود.','']
    if not rows: lines.append('هنوز هیولایی ثبت نشده؛ به ماجراجویی برو و اولین دشمن را شکست بده.')
    for entry,monster in rows: lines.append(f"{html.escape(monster.name)} · نوع {html.escape(getattr(monster,'tier','normal'))} · شکست‌ها: <b>{entry.kills}</b>")
    await panel(cb,'\n'.join(lines),InlineKeyboardMarkup(inline_keyboard=[back_row()]))

@router.callback_query(F.data=='menu:worldboss')
async def world_boss_menu(cb:CallbackQuery):
    b=await ensure_world_boss()
    async with AsyncSessionLocal() as s:
        char=await s.scalar(select(Character).where(Character.telegram_id==cb.from_user.id))
        contribution=await s.scalar(select(WorldBossContribution).where(WorldBossContribution.boss_id==b['id'],WorldBossContribution.character_id==char.id)) if char else None
    pct=max(0,min(100,int((b['hp']/max(1,b['max_hp']))*100)))
    bar='🟩'* (pct//10)+'⬛'*(10-pct//10)
    text=f"🐉 <b>یورش به اژدهای باستانی · Lv.1</b>\n\n{html.escape(b['name'])}\n{bar} {pct}%\n❤️ HP: <b>{b['hp']:,}/{b['max_hp']:,}</b>\n\nآسیب تو: <b>{contribution.damage if contribution else 0:,}</b>\nحملات تو: <b>{contribution.attacks if contribution else 0}</b>\n\nهر ۲۰ ثانیه یک حمله مجاز است. هنگام شکست باس، مشارکت‌کنندگان پاداش دریافت می‌کنند."
    rows=[]
    if b['status']=='active': rows.append([InlineKeyboardButton(text='⚔️ حمله به باس',callback_data='worldboss:attack')])
    rows.append([InlineKeyboardButton(text='🔄 تازه‌سازی',callback_data='menu:worldboss')]);rows.append(back_row())
    await panel(cb,text,InlineKeyboardMarkup(inline_keyboard=rows))

@router.callback_query(F.data=='worldboss:attack')
async def world_boss_attack(cb:CallbackQuery):
    ok,msg,result=await attack_world_boss(cb.from_user.id)
    if not ok:
        await cb.answer(msg,show_alert=True);return
    await cb.answer(msg[:180],show_alert=True)
    await world_boss_menu(cb)

@router.callback_query(F.data == 'menu:marketplace')
async def marketplace_menu(cb: CallbackQuery):
    _, active_market_count = await list_market_page(page=0, page_size=1)
    own = await get_owned_market_listings(cb.from_user.id)
    text = (
        '🏪 <b>بازار بازیکنان اِلدوریا</b>\n\n'
        f'🛒 آگهی‌های فعال قابل مشاهده: <b>{active_market_count:,}</b>\n'
        f'📦 آگهی‌های فعال خودت: <b>{len(own)}</b>\n\n'
        'از بخش «آگهی‌های بازار» برای خرید و از «آگهی‌های من» برای ویرایش قیمت یا لغو آگهی استفاده کن.\n'
        'لغو آگهی، آیتم‌های فروخته‌نشده را به صندوقچه برمی‌گرداند.'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛒 آگهی‌های بازار', callback_data='market:browse')],
        [InlineKeyboardButton(text='📦 آگهی‌های من · ویرایش / لغو', callback_data='market:mine')],
        [InlineKeyboardButton(text='➕ ثبت آگهی از صندوقچه', callback_data='market:sell:home')],
        [InlineKeyboardButton(text='❔ راهنمای بازار', callback_data='market:help')],
        back_row(),
    ])
    await panel(cb, text, kb, panel_name='shop')


@router.callback_query(F.data.startswith('market:browse'))
async def marketplace_browse(cb: CallbackQuery, page_override: int | None = None, kind_override: str | None = None):
    # market:browse:<page>:<kind>; kind can be all, item, equipment
    parts = (cb.data or '').split(':')
    try:
        page = max(0, int(page_override if page_override is not None else (parts[2] if len(parts) > 2 else 0)))
    except ValueError:
        page = 0
    kind = kind_override if kind_override in {'all', 'item', 'equipment'} else (parts[3] if len(parts) > 3 and parts[3] in {'all', 'item', 'equipment'} else 'all')
    page_size = 6
    listings, total = await list_market_page(page=page, page_size=page_size, item_kind=None if kind == 'all' else kind)
    if total and page * page_size >= total:
        page = max(0, (total - 1) // page_size)
        listings, total = await list_market_page(page=page, page_size=page_size, item_kind=None if kind == 'all' else kind)

    lines = [
        '🏪 <b>بازار بازیکنان اِلدوریا</b>',
        '━━━━━━━━━━━━━━━━━━',
        f'🧾 آگهی‌ها: <b>{total:,}</b>  ·  صفحه <b>{page + 1}</b>',
        'قیمت نمایش‌داده‌شده برای هر آگهی، قیمت کل همان بسته است.',
        ''
    ]
    rows = []
    if not listings:
        lines.append('🌙 فعلاً آگهی‌ای در این دسته وجود ندارد.')
        lines.append('می‌توانی اولین آگهی را از صندوقچه ثبت کنی.')
    else:
        seller_ids = {listing.seller_telegram_id for listing, _ in listings}
        async with AsyncSessionLocal() as session:
            sellers = (await session.scalars(select(Character).where(Character.telegram_id.in_(seller_ids)))).all() if seller_ids else []
        seller_map = {seller.telegram_id: seller for seller in sellers}
        for listing, obj in listings:
            seller = seller_map.get(listing.seller_telegram_id)
            seller_label = f'@{seller.telegram_username}' if seller and seller.telegram_username else (seller.name if seller else 'قهرمان اِلدوریا')
            total_price = listing.unit_price * listing.quantity
            type_label = '🛡 تجهیز' if listing.item_kind == 'equipment' else '📦 آیتم'
            lines.append(
                f'{type_label} <b>{html.escape(obj.name)}</b>\n'
                f'├ تعداد: <b>{listing.quantity:,}</b>\n'
                f'├ قیمت هر عدد: <b>{listing.unit_price:,} Gold</b>\n'
                f'├ قیمت کل: <b>{total_price:,} Gold</b>\n'
                f'└ فروشنده: {html.escape(seller_label)} · آگهی #{listing.id}'
            )
            if listing.seller_telegram_id != cb.from_user.id:
                rows.append([InlineKeyboardButton(
                    text=f'🛒 خرید · {total_price:,} Gold',
                    callback_data=f'market:buy:{listing.id}:{page}:{kind}'
                )])
            lines.append('')
    rows.append([
        InlineKeyboardButton(text='همه', callback_data=f'market:browse:{page}:all'),
        InlineKeyboardButton(text='📦 آیتم‌ها', callback_data=f'market:browse:{page}:item'),
        InlineKeyboardButton(text='🛡 تجهیزات', callback_data=f'market:browse:{page}:equipment'),
    ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text='⬅️ قبلی', callback_data=f'market:browse:{page-1}:{kind}'))
    if (page + 1) * page_size < total:
        nav.append(InlineKeyboardButton(text='بعدی ➡️', callback_data=f'market:browse:{page+1}:{kind}'))
    if nav:
        rows.append(nav)
    rows.extend([
        [InlineKeyboardButton(text='📦 آگهی‌های من', callback_data='market:mine'),
         InlineKeyboardButton(text='➕ فروش از صندوقچه', callback_data='market:sell:home')],
        [InlineKeyboardButton(text='❔ راهنمای بازار', callback_data='market:help')],
        back_row('menu:marketplace'),
    ])
    await panel(cb, '\n'.join(lines), InlineKeyboardMarkup(inline_keyboard=rows), panel_name='shop')


@router.callback_query(F.data == 'market:mine')
async def marketplace_mine(cb: CallbackQuery):
    own = await get_owned_market_listings(cb.from_user.id)
    lines = ['📦 <b>آگهی‌های فعال من</b>', 'برای تغییر قیمت از «ویرایش قیمت» و برای برگرداندن آیتم‌ها از «لغو آگهی» استفاده کن.', '']
    rows = []
    if not own:
        lines.append('آگهی فعالی نداری. می‌توانی از صندوقچه یک آگهی ثبت کنی.')
    for listing in own:
        async with AsyncSessionLocal() as session:
            if listing.item_kind == 'item':
                obj = await session.scalar(select(Item).where(Item.id == listing.item_id))
            else:
                obj = await session.scalar(select(Equipment).where(Equipment.id == listing.item_id))
        name = obj.name if obj else f'{listing.item_kind} #{listing.item_id}'
        total = listing.unit_price * listing.quantity
        lines.append(f'#{listing.id} · {html.escape(name)} ×{listing.quantity} · {listing.unit_price:,} گلد/عدد · کل {total:,} گلد')
        rows.append([InlineKeyboardButton(text=f'✏️ ویرایش قیمت #{listing.id}', callback_data=f'market:edit:{listing.id}')])
        rows.append([InlineKeyboardButton(text=f'↩️ لغو آگهی #{listing.id}', callback_data=f'market:cancel:{listing.id}')])
    rows.extend([[InlineKeyboardButton(text='➕ ثبت آگهی', callback_data='market:sell:home')], back_row('menu:marketplace')])
    await panel(cb, '\n'.join(lines), InlineKeyboardMarkup(inline_keyboard=rows), panel_name='shop')


@router.callback_query(F.data.startswith('market:edit:'))
async def marketplace_edit_start(cb: CallbackQuery, state: FSMContext):
    try:
        listing_id = int((cb.data or '').rsplit(':', 1)[-1])
    except ValueError:
        await cb.answer('شناسهٔ آگهی معتبر نیست.', show_alert=True); return
    own = await get_owned_market_listings(cb.from_user.id)
    listing = next((x for x in own if x.id == listing_id), None)
    if listing is None:
        await cb.answer('این آگهی فعال متعلق به تو نیست.', show_alert=True); return
    await state.clear()
    await state.update_data(market_edit_listing_id=listing_id)
    await state.set_state(MarketSellStates.waiting_edit_price)
    await cb.message.answer(f'✏️ قیمت جدید آگهی #{listing_id} را به گلد برای هر عدد بفرست.\nقیمت فعلی: {listing.unit_price:,}\nبرای لغو این کار، عبارت «لغو» را بفرست.')
    await cb.answer()


@router.message(Command('cancel'), MarketSellStates.waiting_edit_price)
async def marketplace_edit_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('ویرایش قیمت لغو شد.')


@router.message(F.text.func(lambda text: bool(text) and text.strip() in {"لغو", "انصراف"}), MarketSellStates.waiting_edit_price)
async def marketplace_edit_cancel_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('ویرایش قیمت لغو شد.')


@router.message(MarketSellStates.waiting_edit_price)
async def marketplace_edit_submit(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        price = int((message.text or '').strip().replace(',', '').replace('٬', ''))
    except ValueError:
        await message.answer('لطفاً فقط عدد قیمت را بفرست.'); return
    ok, result = await update_market_listing_price(message.from_user.id, int(data.get('market_edit_listing_id', 0)), price)
    await state.clear()
    await message.answer(('✅ ' if ok else '❌ ') + result)
@router.callback_query(F.data == 'market:sell:home')
async def marketplace_sell_home(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📦 فروش آیتم‌ها و مواد', callback_data='market:sell:list:item')],
        [InlineKeyboardButton(text='🛡 فروش تجهیزاتِ خارج از تن', callback_data='market:sell:list:equipment')],
        back_row('menu:marketplace'),
    ])
    await panel(cb, '📦 <b>فروش از صندوقچه</b>\nنوع موجودی را انتخاب کن. بعد از انتخاب کالا، تعداد و قیمت هر عدد را وارد می‌کنی.', kb, panel_name='shop')

@router.callback_query(F.data.startswith('market:sell:list:'))
async def marketplace_sell_list(cb: CallbackQuery):
    kind = (cb.data or '').rsplit(':', 1)[-1]
    rows = await (get_inventory_item_ids(cb.from_user.id) if kind == 'item' else get_inventory_equipment_ids(cb.from_user.id))
    title = 'آیتم‌ها و مواد' if kind == 'item' else 'تجهیزاتِ خارج از تن'
    buttons = []
    lines = [f'📦 <b>{title}</b>', 'برای انتخاب کالا روی دکمهٔ آن بزن:', '']
    for owned, obj in rows[:30]:
        if kind == 'equipment' and (owned.equipped or int(getattr(owned, 'enhancement_level', 0) or 0) > 0):
            continue
        label = f'{obj.name} · {owned.quantity} عدد'
        lines.append(f'• {html.escape(obj.name)} ×{owned.quantity}')
        buttons.append([InlineKeyboardButton(text=label[:60], callback_data=f'market:sell:choose:{kind}:{obj.id}')])
    if not buttons:
        lines.append('مورد قابل فروش پیدا نشد. تجهیزات پوشیده‌شده یا ارتقایافته در بازار قابل ثبت نیستند.')
    buttons.append(back_row('market:sell:home'))
    await panel(cb, '\n'.join(lines), InlineKeyboardMarkup(inline_keyboard=buttons), panel_name='shop')

@router.callback_query(F.data.startswith('market:sell:choose:'))
async def marketplace_sell_choose(cb: CallbackQuery, state: FSMContext):
    try:
        _, _, _, kind, raw_id = (cb.data or '').split(':', 4)
        object_id = int(raw_id)
    except (ValueError, TypeError):
        await cb.answer('کالای انتخاب‌شده معتبر نیست.', show_alert=True); return
    rows = await (get_inventory_item_ids(cb.from_user.id) if kind == 'item' else get_inventory_equipment_ids(cb.from_user.id))
    found = next(((owned, obj) for owned, obj in rows if obj.id == object_id), None)
    if not found:
        await cb.answer('این کالا دیگر در صندوقچه نیست.', show_alert=True); return
    owned, obj = found
    if kind == 'equipment' and (owned.equipped or int(getattr(owned, 'enhancement_level', 0) or 0) > 0):
        await cb.answer('این تجهیز قابل فروش نیست؛ از تن خارجش کن و تجهیز ارتقایافته را نمی‌توان در بازار گذاشت.', show_alert=True); return
    await state.update_data(market_kind=kind, market_item_id=object_id, market_item_name=obj.name, market_max_quantity=int(owned.quantity))
    await state.set_state(MarketSellStates.waiting_quantity_price)
    await cb.answer()
    await cb.message.answer(
        f'🧾 <b>ثبت آگهی بازار</b>\n━━━━━━━━━━━━━━━━━━\n'
        f'کالا: <b>{html.escape(obj.name)}</b>\n'
        f'موجودی قابل فروش: <b>{owned.quantity:,}</b> عدد\n\n'
        'در <b>یک پیام</b> این دو عدد را بفرست:\n'
        '<code>تعداد قیمت_هر_عدد</code>\n'
        'مثال: <code>5 1300</code>\n'
        'یعنی ۵ عدد، هر عدد ۱۳۰۰ گلد.\n\n'
        'برای لغو عملیات، عبارت «لغو» را بفرست.',
        parse_mode='HTML'
    )

@router.message(Command('cancel'), MarketSellStates.waiting_quantity_price)
async def marketplace_sell_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('ثبت آگهی لغو شد.')

@router.message(F.text.func(lambda text: bool(text) and text.strip() in {"لغو", "انصراف"}), MarketSellStates.waiting_quantity_price)
async def marketplace_sell_cancel_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('ثبت آگهی لغو شد.')


@router.message(MarketSellStates.waiting_quantity_price)
async def marketplace_sell_submit(message: Message, state: FSMContext):
    if not message.from_user or not message.text:
        return
    data = await state.get_data()
    # Accept both the recommended "6 1" format and natural labels such as
    # "6 عدد اسکرول و قیمت هر عدد 1". Normalize Persian/Arabic digits first.
    raw = message.text.translate(str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )).replace(',', '').replace('٬', '').replace('،', ' ').replace('_', ' ')
    import re
    parts = re.findall(r'(?<![A-Za-z])\d+(?![A-Za-z])', raw)
    if len(parts) != 2:
        await message.answer(
            '⚠️ تعداد و قیمت هر عدد را در یک پیام بفرست.\n'
            'مثال: <code>6 1</code> یعنی ۶ عدد، هر عدد ۱ گلد.',
            parse_mode='HTML',
        )
        return
    quantity, unit_price = map(int, parts)
    if quantity < 1 or quantity > int(data.get('market_max_quantity', 0)) or unit_price < 1:
        await message.answer(f'تعداد باید بین ۱ و {data.get("market_max_quantity", 0)} باشد و قیمت هم حداقل ۱ گلد.'); return
    kind = data.get('market_kind')
    try:
        if kind == 'equipment':
            ok, result = await create_equipment_market_listing(message.from_user.id, int(data['market_item_id']), quantity, unit_price)
        elif kind == 'item':
            ok, result = await create_market_listing(message.from_user.id, int(data['market_item_id']), quantity, unit_price)
        else:
            await state.clear()
            await message.answer('نوع کالای انتخاب‌شده معتبر نیست؛ دوباره از بازار شروع کن.')
            return
    except Exception:
        # Do not swallow the error silently: log the traceback and give a usable reply.
        import logging
        logging.getLogger(__name__).exception('Player market listing failed for telegram_id=%s', message.from_user.id)
        await message.answer('❌ ثبت آگهی به خطا خورد. جزئیات در گزارش اجرای ربات ثبت شد؛ موجودی تو بدون تأیید تراکنش تغییر داده نمی‌شود.')
        return
    await state.clear()
    await message.answer(('✅ ' if ok else '❌ ') + html.escape(str(result)), parse_mode='HTML')

@router.callback_query(F.data.startswith('market:buy:'))
async def marketplace_buy(cb: CallbackQuery):
    parts = (cb.data or '').split(':')
    try:
        listing_id = int(parts[2])
        page = max(0, int(parts[3])) if len(parts) > 3 else 0
    except (ValueError, IndexError):
        await cb.answer('شناسهٔ آگهی معتبر نیست.', show_alert=True)
        return
    kind = parts[4] if len(parts) > 4 and parts[4] in {'all', 'item', 'equipment'} else 'all'
    ok, msg = await buy_market_listing(cb.from_user.id, listing_id)
    if not ok:
        await cb.answer(msg[:180], show_alert=True)
        return
    await cb.answer('✅ خرید با موفقیت انجام شد.', show_alert=True)
    await marketplace_browse_page_after_buy(cb, page, kind)


async def marketplace_browse_page_after_buy(cb: CallbackQuery, page: int, kind: str):
    await marketplace_browse(cb, page_override=page, kind_override=kind)


@router.message(Command('market_sell'))
async def marketplace_sell(message:Message):
    if not message.from_user or not message.text:return
    parts=message.text.split()
    if len(parts)!=4:
        await message.answer('روش استفاده:\n<code>/market_sell ITEM_ID QUANTITY PRICE_PER_ITEM</code>',parse_mode='HTML');return
    try: item_id,qty,price=map(int,parts[1:])
    except ValueError: await message.answer('سه مقدار باید عدد باشند.');return
    ok,msg=await create_market_listing(message.from_user.id,item_id,qty,price)
    await message.answer(('✅ ' if ok else '❌ ')+html.escape(msg),parse_mode='HTML')

@router.message(Command('market_equipment', 'market_equipment_items'))
async def marketplace_equipment_ids(message:Message):
    if not message.from_user:
        return
    rows = await get_inventory_equipment_ids(message.from_user.id)
    if not rows:
        await message.answer('تجهیزی در صندوقچه نداری.')
        return
    lines = ['🛡️ <b>تجهیزات قابل فروش</b>']
    for owned, equipment in rows[:40]:
        state = ' · پوشیده‌شده (ابتدا از تن خارج کن)' if owned.equipped else ''
        lines.append(f'ID <code>{equipment.id}</code> · {html.escape(equipment.name)} ×{owned.quantity} · +{owned.enhancement_level}{state}')
    lines.append('\nبرای فروش: <code>/market_sell_equipment EQUIPMENT_ID QUANTITY PRICE_PER_ITEM</code>')
    await message.answer('\n'.join(lines), parse_mode='HTML')

@router.message(Command('market_sell_equipment'))
async def marketplace_sell_equipment(message:Message):
    if not message.from_user or not message.text:
        return
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer('روش استفاده:\n<code>/market_sell_equipment EQUIPMENT_ID QUANTITY PRICE_PER_ITEM</code>', parse_mode='HTML')
        return
    try:
        equipment_id, quantity, price = map(int, parts[1:])
    except ValueError:
        await message.answer('شناسه، تعداد و قیمت باید عدد باشند.')
        return
    ok, msg = await create_equipment_market_listing(message.from_user.id, equipment_id, quantity, price)
    await message.answer(('✅ ' if ok else '❌ ') + html.escape(msg), parse_mode='HTML')

@router.callback_query(F.data.startswith('market:cancel:'))
async def marketplace_cancel(cb:CallbackQuery):
    try: listing_id=int((cb.data or '').rsplit(':',1)[-1])
    except ValueError: await cb.answer('آگهی معتبر نیست.',show_alert=True);return
    ok,msg=await cancel_market_listing(cb.from_user.id,listing_id)
    await cb.answer(msg,show_alert=not ok)
    if ok: await marketplace_mine(cb)


@router.message(Command('market_items'))
async def marketplace_inventory_ids(message:Message):
    if not message.from_user:return
    rows=await get_inventory_item_ids(message.from_user.id)
    if not rows: await message.answer('آیتم قابل معامله‌ای در صندوقچه نداری.');return
    lines=['📦 <b>آیتم‌های قابل فروش</b>']
    for inv,item in rows[:40]: lines.append(f'ID <code>{item.id}</code> · {html.escape(item.name)} ×{inv.quantity}')
    lines.append('\nبرای فروش: <code>/market_sell ITEM_ID QUANTITY PRICE_PER_ITEM</code>')
    await message.answer('\n'.join(lines),parse_mode='HTML')

@router.callback_query(F.data=='menu:forge')
async def forge_menu(cb:CallbackQuery):
    async with AsyncSessionLocal() as s:
        char=await s.scalar(select(Character).where(Character.telegram_id==cb.from_user.id))
        owned=(await s.execute(select(CharacterEquipment,Equipment).join(Equipment,Equipment.id==CharacterEquipment.equipment_id).where(CharacterEquipment.character_id==char.id,CharacterEquipment.quantity>0).order_by(CharacterEquipment.enhancement_level,Equipment.required_level).limit(25))).all() if char else []
    rows=[];lines=['⚒️ <b>آهنگری اِلدوریا</b>','هر ارتقا +۵٪ از آمار پایهٔ همان قطعه را به آن اضافه می‌کند. سقف ارتقا: +10.','']
    set_labels = {"eldoria_guardian": "نگهبان اِلدوریا", "arcane_storm": "طوفان آرکین", "dragon_emperor": "امپراتور اژدها", "moonshadow": "سایه ماه"}
    set_counts = {}
    for ce, e in owned:
        if e.set_key:
            set_counts[e.set_key] = set_counts.get(e.set_key, 0) + 1
    if set_counts:
        lines.append('🧩 <b>پیشرفت ست‌های در اختیار</b>')
        for key, count in set_counts.items():
            lines.append(f"{html.escape(set_labels.get(key, key))}: {count}/6 قطعه")
        lines.append('پاداش ست هنگام پوشیدن ۲، ۴ یا ۶ قطعهٔ هم‌نام به‌صورت خودکار در Stats محاسبه می‌شود.')
    for ce,e in owned:
        cost=500*(int(ce.enhancement_level or 0)+1)**2
        material_name,material_qty = (('🌿 گیاه اِلدوریا',1) if ce.enhancement_level < 3 else ('⛏️ تکه‌آهن گابلین',2) if ce.enhancement_level < 6 else ('💎 خرده‌سنگ جادویی',2) if ce.enhancement_level < 8 else ('🔥 فلس اژدها',1))
        set_text = f" · ست {set_labels.get(e.set_key, e.set_key)}" if e.set_key else ''
        lines.append(f"{html.escape(e.name)} · +{ce.enhancement_level}{html.escape(set_text)} · {cost:,} Gold + {material_name} ×{material_qty}")
        if ce.enhancement_level<10: rows.append([InlineKeyboardButton(text=f'⚒️ ارتقای {e.name} +{ce.enhancement_level}',callback_data=f'forge:up:{e.id}')])
    if not owned:lines.append('تجهیزی برای ارتقا در صندوقچه نداری.')
    rows.append(back_row())
    await panel(cb,'\n'.join(lines),InlineKeyboardMarkup(inline_keyboard=rows))

@router.callback_query(F.data.startswith('forge:up:'))
async def forge_upgrade(cb:CallbackQuery):
    try: equipment_id=int((cb.data or '').rsplit(':',1)[-1])
    except ValueError: await cb.answer('تجهیز نامعتبر است.',show_alert=True);return
    ok,msg=await upgrade_equipment(cb.from_user.id,equipment_id)
    if not ok: await cb.answer(msg,show_alert=True);return
    await cb.answer(msg[:180],show_alert=True);await forge_menu(cb)

@router.callback_query(F.data=='pets:evolve')
async def pet_evolve(cb:CallbackQuery):
    ok,msg=await evolve_active_pet(cb.from_user.id)
    await cb.answer(msg[:180],show_alert=not ok)
    if ok: await pets_menu_for_user(cb)

async def pets_menu_for_user(cb:CallbackQuery):
    owned=await active_pets(cb.from_user.id)
    rows=[];lines=['🐾 <b>همراهان قهرمان</b>','پت فعال، آمار قهرمان را تقویت می‌کند. تمرین پت سطح و مرحلهٔ تکاملش را بالا می‌برد.','']
    if not owned: lines.append('هنوز پتی نداری. از بازار پت یکی تهیه کن.')
    for pet,cp in owned:
        lines.append(f"{'🟢' if cp.active else '⚪'} {html.escape(pet.name)} · {pet.rarity} · Lv.{cp.level} · تکامل {cp.evolution_stage}\nATK +{pet.bonus_attack} · DEF +{pet.bonus_defense} · HP +{pet.bonus_hp}")
        if cp.last_training_at and cp.training_completed_at is None:
            remaining=max(0,3600-int((datetime.utcnow()-cp.last_training_at).total_seconds()))
            lines.append(f"⏳ وضعیت: در حال آموزش · زمان باقی‌مانده: {remaining//60} دقیقه و {remaining%60} ثانیه")
        if not cp.active: rows.append([InlineKeyboardButton(text=f'🐾 فعال‌کردن {pet.name}',callback_data=f'pets:activate:{pet.id}')])
    rows.append([InlineKeyboardButton(text='✨ تمرین/تکامل پت فعال',callback_data='pets:evolve')]);rows.append([InlineKeyboardButton(text='🛒 بازار پت‌ها',callback_data='pets:market')]);rows.append(back_row())
    await panel(cb,'\n\n'.join(lines),InlineKeyboardMarkup(inline_keyboard=rows))

@router.callback_query(F.data=='pets:market')
async def pets_market(cb:CallbackQuery):
    async with AsyncSessionLocal() as s:
        pets=list((await s.scalars(select(Pet).where(Pet.is_active.is_(True)).order_by(Pet.price))).all())
    rows=[];lines=['🐾 <b>بازار پت‌ها</b>','هر پت فقط یک‌بار برای هر قهرمان قابل خرید است.','']
    for pet in pets:
        lines.append(f"{html.escape(pet.name)} · {pet.rarity}\nATK +{pet.bonus_attack} · DEF +{pet.bonus_defense} · HP +{pet.bonus_hp} · {pet.price:,} Gold")
        rows.append([InlineKeyboardButton(text=f'خرید {pet.name} · {pet.price:,} Gold',callback_data=f'pets:buy:{pet.id}')])
    rows.append(back_row('menu:pets'))
    await panel(cb,'\n\n'.join(lines),InlineKeyboardMarkup(inline_keyboard=rows))

@router.callback_query(F.data.startswith('pets:buy:'))
async def pets_buy(cb:CallbackQuery):
    try: pet_id=int((cb.data or '').rsplit(':',1)[-1])
    except ValueError: await cb.answer('پت نامعتبر است.',show_alert=True);return
    async with AsyncSessionLocal() as s:
        char=await s.scalar(select(Character).where(Character.telegram_id==cb.from_user.id).with_for_update())
        pet=await s.scalar(select(Pet).where(Pet.id==pet_id,Pet.is_active.is_(True)))
        if not char or not pet: msg='قهرمان یا پت پیدا نشد.';ok=False
        elif char.gold<pet.price:msg='Gold کافی نداری.';ok=False
        elif await s.scalar(select(CharacterPet.id).where(CharacterPet.character_id==char.id,CharacterPet.pet_id==pet.id)):msg='این پت را قبلاً خریده‌ای.';ok=False
        else:
            char.gold-=pet.price;s.add(CharacterPet(character_id=char.id,pet_id=pet.id,active=False,level=1,xp=0,evolution_stage=0));await s.commit();msg=f'پت «{pet.name}» به همراهانت اضافه شد.';ok=True
    await cb.answer(msg,show_alert=not ok)
    if ok: await pets_menu_for_user(cb)

@router.callback_query(F.data.startswith('pets:activate:'))
async def pets_activate(cb:CallbackQuery):
    try: pet_id=int((cb.data or '').rsplit(':',1)[-1])
    except ValueError: await cb.answer('پت نامعتبر است.',show_alert=True);return
    ok,msg=await activate_pet(cb.from_user.id,pet_id)
    await cb.answer(msg,show_alert=not ok)
    if ok: await pets_menu_for_user(cb)


# ---------------------------------------------------------------------------
# راهنمای یکپارچهٔ بازی
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "menu:guide")
async def game_guide(cb: CallbackQuery):
    text = (
        "📖 <b>راهنمای دنیای فانتزی الدوریا</b>\n\n"
        "<b>👤 پروفایل</b>\nنمایش سطح، نژاد، آمار، گلد، جم و فن‌آرت انتخابی. اگر فن‌آرت نداشته باشی، تصویر تلگرام نمایش داده می‌شود.\n\n"
        "<b>🗃 صندوقچه</b>\nآیتم‌ها و مواد اولیه‌ات را ببین؛ تجهیزات را از بخش تجهیزات بپوش یا از مواد برای ساخت استفاده کن.\n\n"
        "<b>⚔️ مهارت‌ها</b>\nمهارت‌ها را یاد بگیر و ارتقا بده؛ هزینهٔ مانا و قدرت هر مهارت را پیش از استفاده بررسی کن.\n\n"
        "<b>🛡 تجهیزات و ⚒ آهنگری</b>\nتجهیزات را از فروشگاه بخر، بپوش و با گلد و مواد لازم ارتقا بده. سطح موردنیاز هر قطعه را بررسی کن.\n\n"
        "<b>🗺 ماجراجویی و 🏰 دانجن</b>\nبا هیولاها بجنگ و XP، گلد و مواد به دست بیاور. دانجن گروهی برای همکاری با اعضای پارتی است.\n\n"
        "<b>📜 مأموریت‌ها</b>\nپیشرفت مأموریت‌ها را دنبال کن و پس از تکمیل، پاداش را دریافت کن. هر پاداش فقط یک بار قابل دریافت است.\n\n"
        "<b>🐾 پت‌ها</b>\nپت بخر، یکی را فعال کن و برای تقویت آن تمرین بده. هر پت هر ۶۰ دقیقه یک بار قابل تمرین است.\n\n"
        "<b>🏪 بازار بازیکنان</b>\nاز دکمهٔ «بازار بازیکنان» وارد شو. برای فروش، «ثبت آگهی از صندوقچه» را بزن، نوع کالا و سپس خود کالا را انتخاب کن و تعداد و قیمت هر عدد را در یک پیام بنویس؛ مثلاً <code>3 500</code> یعنی ۳ عدد، هرکدام ۵۰۰ گلد. برای خرید، آگهی‌های بازار را ببین. از «آگهی‌های من» هم می‌توانی قیمت را تغییر بدهی یا آگهی را لغو کنی. برای فروش تجهیزات، آن‌ها باید از تن خارج شده باشند.\n\n"
        "<b>💱 گلد و جم</b>\nگلد برای خریدهای معمولی و جم برای تجهیزات ویژه است. در بخش تبدیل ارز، نرخ و مقدار دریافتی را پیش از تأیید می‌بینی.\n\n"
        "<b>👥 پارتی، 🛡 گیلد، 🏆 رتبه‌بندی و ⚔️ PvP</b>\nبرای بازی گروهی، عضویت در گیلد، دیدن رتبه‌ها و مبارزه با بازیکنان از این بخش‌ها استفاده کن.\n\n"
        "<b>🎨 فن‌آرت و ⚙️ تنظیمات</b>\nفن‌آرت‌های خودت را مدیریت کن و تنظیمات قابل‌دسترسی حساب را تغییر بده.\n\n"
        "<b>🧭 کار با ربات</b>\nبرای ورود به بخش‌ها از دکمه‌های منو یا نوشتن نام فارسی بخش استفاده کن؛ مثلاً «بازار بازیکنان»."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💱 تبدیل گلد به جم", callback_data="menu:exchange")],
        [InlineKeyboardButton(text="🏪 بازار بازیکنان", callback_data="menu:marketplace")],
        [InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="menu:back")],
    ])
    # The guide is longer than Telegram's 1024-character photo-caption limit.
    # Render it as a text panel instead of using the main-menu image caption.
    await show_panel(
        callback=cb,
        panel_name="guide",
        text=text,
        reply_markup=kb,
        parse_mode="HTML",
    )
    try:
        await cb.answer()
    except Exception:
        pass


@router.message(Command("guide", ignore_case=True))
@router.message(F.text.regexp(r"(?i)^\s*(راهنما|راهنمای بازی|راهنمای الدرویا|راهنمای الدوریا)\s*$"))
async def game_guide_command(message: Message):
    text = (
        "📖 <b>راهنمای دنیای فانتزی الدوریا</b>\n\n"
        "👤 <b>پروفایل:</b> /profile\n"
        "🗃 <b>صندوقچه:</b> از منوی اصلی، بخش صندوقچه را باز کن.\n"
        "⚔️ <b>نبرد با باس گروه:</b> روی پیام باس ریپلای کن و «حمله» بنویس؛ یا از /attack استفاده کن.\n"
        "✨ <b>جادو:</b> روی پیام باس ریپلای کن و /magic یا «جادو» را بفرست.\n"
        "🧪 <b>معجون سلامتی:</b> /heal یا «هیل»\n"
        "🔷 <b>معجون مانا:</b> /mana یا «ریکاوری مانا»\n"
        "🐾 <b>پت:</b> /mypet\n"
        "🏪 <b>فروشگاه:</b> /shop\n"
        "🎨 <b>فن‌آرت:</b> /arts یا «ارت ها»\n\n"
        "برای توضیحات کامل‌تر، از منوی اصلی دکمهٔ «راهنما» را انتخاب کن."
    )
    await message.answer(text, parse_mode="HTML")

# ---------------------------------------------------------------------------
# تبدیل ارز امن با نرخ ثابت و شفاف
# ---------------------------------------------------------------------------
GOLD_PER_GEM = 10000

@router.callback_query(F.data == "menu:exchange")
async def exchange_menu(cb: CallbackQuery):
    async with AsyncSessionLocal() as session:
        char = await session.scalar(select(Character).where(Character.telegram_id == cb.from_user.id))
    if not char:
        await cb.answer("ابتدا با /start حساب بساز.", show_alert=True)
        return
    max_gems = max(0, int(char.gold) // GOLD_PER_GEM)
    rows = []
    for amount in (1, 5, 10):
        if max_gems >= amount:
            rows.append([InlineKeyboardButton(
                text=f"💱 تبدیل {amount * GOLD_PER_GEM:,} گلد به {amount} جم",
                callback_data=f"exchange:confirm:{amount}",
            )])
    if max_gems == 0:
        rows.append([InlineKeyboardButton(text="گلد کافی برای تبدیل نداری", callback_data="exchange:noop")])
    rows.append(back_row())
    text = (
        "💱 <b>صرافی اِلدوریا</b>\n\n"
        f"نرخ تبدیل: <b>{GOLD_PER_GEM:,} گلد = ۱ جم</b>\n"
        f"موجودی تو: 💰 {char.gold:,} گلد · 💎 {char.gems:,} جم\n\n"
        "هر بار پیش از تبدیل، مقدار گلد مصرفی و جم دریافتی مشخص است. تبدیل پس از تأیید نهایی انجام می‌شود و قابل برگشت نیست."
    )
    await panel(cb, text, InlineKeyboardMarkup(inline_keyboard=rows))

@router.callback_query(F.data == "exchange:noop")
async def exchange_noop(cb: CallbackQuery):
    await cb.answer("برای تبدیل حداقل ۱۰٬۰۰۰ گلد نیاز داری.", show_alert=True)

@router.callback_query(F.data.startswith("exchange:confirm:"))
async def exchange_confirm(cb: CallbackQuery):
    from sqlalchemy import update
    try:
        gems = int((cb.data or "").rsplit(":", 1)[-1])
    except ValueError:
        await cb.answer("مقدار تبدیل نامعتبر است.", show_alert=True)
        return
    if gems not in (1, 5, 10):
        await cb.answer("مقدار تبدیل نامعتبر است.", show_alert=True)
        return
    cost = gems * GOLD_PER_GEM
    async with AsyncSessionLocal() as session:
        char = await session.scalar(
            select(Character).where(Character.telegram_id == cb.from_user.id).with_for_update()
        )
        if not char:
            ok, msg = False, "قهرمان پیدا نشد."
        elif char.gold < cost:
            ok, msg = False, "گلد کافی نداری."
        else:
            char.gold -= cost
            char.gems += gems
            await session.commit()
            ok, msg = True, f"تبدیل انجام شد: {cost:,} گلد به {gems} جم تبدیل شد."
    await cb.answer(msg, show_alert=True)
    if ok:
        await exchange_menu(cb)


@router.callback_query(F.data == "market:help")
async def marketplace_help(cb: CallbackQuery):
    text = (
        "❓ <b>راهنمای بازار بازیکنان</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🛍 <b>چطور چیزی بفروشم؟</b>\n"
        "۱) دکمهٔ «ثبت آگهی از صندوقچه» را بزن.\n"
        "۲) «فروش آیتم‌ها و مواد» یا «فروش تجهیزات» را انتخاب کن.\n"
        "۳) روی کالایی که می‌خواهی بفروشی بزن. موجودی قابل فروش همان‌جا نشان داده می‌شود.\n"
        "۴) وقتی از تو خواسته شد، تعداد و قیمت هر عدد را در <b>یک پیام</b> بفرست. مثال: <code>3 500</code> یعنی ۳ عدد با قیمت ۵۰۰ گلد برای هر عدد.\n"
        "۵) آگهی ثبت می‌شود و در فهرست بازار قرار می‌گیرد. تجهیزات باید از تن خارج شده باشند و تجهیزات ارتقایافته قابل ثبت نیستند.\n\n"
        "🛒 <b>چطور بخرم؟</b>\n"
        "وارد «آگهی‌های بازار» شو، قیمت هر عدد و قیمت کل را بررسی کن و دکمهٔ خرید همان آگهی را بزن. گلد از تو کم و کالا به صندوقچه‌ات اضافه می‌شود؛ گلد فروشنده نیز واریز می‌شود. خرید آگهی خودت امکان‌پذیر نیست.\n\n"
        "✏️ <b>ویرایش یا لغو آگهی</b>\n"
        "در «آگهی‌های من» می‌توانی قیمت هر عدد را تغییر بدهی یا آگهی را لغو کنی. با لغو، کالاهای فروش‌نرفته به صندوقچه برمی‌گردند. برای انصراف از واردکردن تعداد یا قیمت، فقط بنویس «لغو».\n\n"
        "💡 <b>نکته</b>\n"
        "قیمت کل برابر تعداد × قیمت هر عدد است؛ پیش از خرید، هر دو مبلغ را بررسی کن."
    )
    await panel(cb, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛒 دیدن آگهی‌های بازار', callback_data='market:browse')],
        [InlineKeyboardButton(text='➕ ثبت آگهی از صندوقچه', callback_data='market:sell:home')],
        [InlineKeyboardButton(text='📦 آگهی‌های من', callback_data='market:mine')],
        back_row('menu:marketplace'),
    ]), panel_name='shop')
