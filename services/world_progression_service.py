from __future__ import annotations
import random
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from database.database import AsyncSessionLocal
from models.character import Character
from models.inventory import Inventory
from models.item import Item
from models.monster import Monster
from models.social_systems import PlayerSetting, CharacterPet, Pet
from models.world_systems import (WorldBoss, WorldBossContribution, MarketListing, CharacterBestiary, CharacterActivity, DailyTaskProgress, NotificationEvent)
from services.xp_service import add_character_xp

MATERIALS = {
    'wolf': ('🦴 پنجهٔ گرگ', 'پنجه‌ای مناسب ساخت تجهیزات سبک', 0.42, 1),
    'goblin': ('⛏️ تکه‌آهن گابلین', 'قطعه‌آهن بازیابی‌شده از تجهیزات گابلین', 0.36, 1),
    'golem': ('🗃 سنگ جادویی', 'سنگی با انرژی جادویی که از هستهٔ گولم به دست می‌آید', 0.30, 1),
    'dragon': ('🔥 فلس اژدها', 'فلس مقاوم با انرژی آتشین', 0.16, 1),
    'default': ('🌿 گیاه اِلدوریا', 'گیاهی کاربردی برای ساخت و معجون‌سازی', 0.24, 1),
}
DAILY_TASKS = {
    'kill_3': {'title':'⚔️ شکارچی تازه‌کار','goal':3,'gold':250,'xp':100,'event':'kill'},
    'kill_8': {'title':'🐺 شکارچی باتجربه','goal':8,'gold':600,'xp':250,'event':'kill'},
    'craft_1': {'title':'🔨 صنعتگر روز','goal':1,'gold':200,'xp':120,'event':'craft'},
    'upgrade_1': {'title':'✨ آهنگر ماهر','goal':1,'gold':300,'xp':150,'event':'upgrade'},
}

def _today(): return datetime.utcnow().date().isoformat()

async def _activity(session, character_id:int, event_type:str, details:str=''):
    session.add(CharacterActivity(character_id=character_id,event_type=event_type,details=details[:1000]))

async def _progress_daily(session, character_id:int, event_type:str, amount:int=1):
    date=_today()
    for key, task in DAILY_TASKS.items():
        if task['event'] != event_type: continue
        row=await session.scalar(select(DailyTaskProgress).where(DailyTaskProgress.character_id==character_id,DailyTaskProgress.task_key==key,DailyTaskProgress.task_date==date))
        if row is None:
            row=DailyTaskProgress(character_id=character_id,task_key=key,task_date=date,progress=0,claimed=False); session.add(row)
        if not row.claimed: row.progress=min(task['goal'],row.progress+amount)

async def record_kill_and_drop(telegram_id:int, monster_id:int|None, variant:str|None=None):
    """Record a real adventure kill and return the exact material drops for the victory report."""
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id).with_for_update())
        if not char: return []
        if monster_id:
            monster=await session.scalar(select(Monster).where(Monster.id==monster_id))
            if monster:
                best=await session.scalar(select(CharacterBestiary).where(CharacterBestiary.character_id==char.id,CharacterBestiary.monster_id==monster.id))
                if best is None:
                    best=CharacterBestiary(character_id=char.id,monster_id=monster.id,kills=0);session.add(best)
                best.kills+=1; best.last_killed_at=datetime.utcnow()
                family=(monster.family or '').lower()
                variant_text=(monster.variant or '').lower()
                if 'dragon' in family or 'dragon' in variant_text or 'drake' in family or 'drake' in variant_text:
                    family='dragon'
            else: family=''
        else: family=''
        await _progress_daily(session,char.id,'kill',1)
        await _activity(session,char.id,'monster_kill',f'monster_id={monster_id};variant={variant or "unknown"}')
        try:
            from services.scroll_service import has_buff
            explorer = await has_buff(telegram_id, 'explorer')
        except Exception:
            explorer = False
        drops=[]
        async def grant_material(name, desc, chance, rarity='common'):
            adjusted_chance = min(.95, chance * (1.30 if explorer else 1.0))
            if random.random() >= adjusted_chance:
                return
            item=await session.scalar(select(Item).where(Item.name==name).limit(1))
            if item is None:
                item=Item(name=name,description=desc,item_type='material',rarity=rarity,sell_price=20,buy_price=0,is_tradeable=True);session.add(item);await session.flush()
            inv=await session.scalar(select(Inventory).where(Inventory.character_id==char.id,Inventory.item_id==item.id).with_for_update())
            if inv is None: session.add(Inventory(character_id=char.id,item_id=item.id,quantity=1))
            else: inv.quantity+=1
            drops.append(f'{name} ×1')
            await _activity(session,char.id,'item_drop',f'{name} x1')
            setting=await session.scalar(select(PlayerSetting).where(PlayerSetting.telegram_id==telegram_id))
            if setting is None or setting.notifications:
                session.add(NotificationEvent(telegram_id=telegram_id,event_type='item_drop',message=f'🎁 غنیمت جدید: {name} ×1',delivered=False))

        name,desc,chance,_qty=MATERIALS.get(family,MATERIALS['default'])
        # Family-specific loot, including wolf claws and dragon scales.
        luck_bonus = 1 + min(int(char.luck or 0),100)/250
        await grant_material(name, desc, min(.8,chance * luck_bonus), 'uncommon' if family in {'golem','dragon'} else 'common')
        # Gathering materials used by the crafting recipes can also be found during any adventure.
        gathering_pool = [
            ('🪵 چوب اِلدوری','چوب مقاوم برای ساخت‌وساز.',0.12),
            ('⛓️ سنگ آهن','سنگ آهن موردنیاز کارگاه.',0.12),
            ('💎 کریستال جادویی','کریستال سرشار از Mana.',0.055),
            ('🌿 گیاه اِلدوریا','گیاهی کاربردی برای ساخت و معجون‌سازی.',0.16),
        ]
        # Golems are the primary source of magical stones; other foes can drop them rarely too.
        gathering_pool.append(('🗃 سنگ جادویی','سنگی با انرژی جادویی.',0.08 if family == 'golem' else 0.025))
        extra_name, extra_desc, extra_chance = random.choice(gathering_pool)
        await grant_material(extra_name, extra_desc, extra_chance, 'rare' if extra_name == '💎 کریستال جادویی' else 'common')
        await session.commit()
        return drops

async def log_progress(telegram_id:int,event_type:str,details:str=''):
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id))
        if not char:return
        await _activity(session,char.id,event_type,details)
        if event_type in {'craft','upgrade'}: await _progress_daily(session,char.id,event_type,1)
        await session.commit()

async def get_daily_tasks(telegram_id:int):
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id))
        if not char:return []
        rows=[]
        for key,task in DAILY_TASKS.items():
            row=await session.scalar(select(DailyTaskProgress).where(DailyTaskProgress.character_id==char.id,DailyTaskProgress.task_key==key,DailyTaskProgress.task_date==_today()))
            rows.append((key,task,row.progress if row else 0,row.claimed if row else False))
        return rows

async def claim_daily_task(telegram_id:int,key:str):
    if key not in DAILY_TASKS:return False,'این مأموریت معتبر نیست.'
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id).with_for_update())
        if not char:return False,'قهرمان پیدا نشد.'
        task=DAILY_TASKS[key]
        row=await session.scalar(select(DailyTaskProgress).where(DailyTaskProgress.character_id==char.id,DailyTaskProgress.task_key==key,DailyTaskProgress.task_date==_today()).with_for_update())
        if not row or row.progress<task['goal']:return False,'هنوز این مأموریت کامل نشده است.'
        if row.claimed:return False,'جایزهٔ این مأموریت قبلاً دریافت شده است.'
        row.claimed=True;char.gold+=task['gold']
        await session.commit()
    await add_character_xp(telegram_id,task['xp'])
    await log_progress(telegram_id,'daily_reward',key)
    return True,f"جایزه دریافت شد: {task['gold']} Gold و {task['xp']} XP"

async def get_bestiary(telegram_id:int):
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id))
        if not char:return []
        rows=(await session.execute(select(CharacterBestiary,Monster).join(Monster,Monster.id==CharacterBestiary.monster_id).where(CharacterBestiary.character_id==char.id).order_by(CharacterBestiary.kills.desc()).limit(15))).all()
        return [(b,m) for b,m in rows]

async def get_history(telegram_id:int):
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id))
        if not char:return []
        return list((await session.scalars(select(CharacterActivity).where(CharacterActivity.character_id==char.id).order_by(CharacterActivity.created_at.desc()).limit(15))).all())

async def ensure_world_boss():
    async with AsyncSessionLocal() as session:
        boss=await session.scalar(select(WorldBoss).where(WorldBoss.boss_key=='eldoria_ancient_dragon').with_for_update())
        if boss is None:
            boss=WorldBoss(boss_key='eldoria_ancient_dragon',name='🐉 اژدهای باستانی اِلدوریا',max_hp=2500,hp=2500,reward_gold=1800,reward_xp=800,status='active');session.add(boss);await session.commit();await session.refresh(boss)
        else:
            # Older builds created this level-1 boss with 250,000 HP, making it impractical.
            # Normalize that legacy value while preserving the remaining-HP percentage.
            if int(boss.max_hp or 0) == 250000:
                ratio = max(0.0, min(1.0, int(boss.hp or 0) / 250000))
                boss.max_hp = 2500
                boss.hp = max(0, min(2500, int(2500 * ratio)))
            if boss.status == 'defeated' and boss.ended_at and boss.ended_at < datetime.utcnow()-timedelta(hours=24):
                await session.execute(delete(WorldBossContribution).where(WorldBossContribution.boss_id==boss.id))
                boss.hp=boss.max_hp; boss.status='active'; boss.started_at=datetime.utcnow(); boss.ended_at=None
            await session.commit()
        return {'id':boss.id,'name':boss.name,'hp':boss.hp,'max_hp':boss.max_hp,'status':boss.status,'reward_gold':boss.reward_gold,'reward_xp':boss.reward_xp}

async def attack_world_boss(telegram_id:int):
    from services.death_service import ensure_character_alive
    alive, alive_message = await ensure_character_alive(telegram_id)
    if not alive: return False, alive_message, None
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id).with_for_update())
        if not char:return False,'قهرمان پیدا نشد.',None
        boss=await session.scalar(select(WorldBoss).where(WorldBoss.boss_key=='eldoria_ancient_dragon').with_for_update())
        if not boss:
            boss=WorldBoss(boss_key='eldoria_ancient_dragon',name='🐉 اژدهای باستانی اِلدوریا',max_hp=2500,hp=2500,reward_gold=1800,reward_xp=800,status='active');session.add(boss);await session.flush()
        if boss.status!='active' or boss.hp<=0:return False,'این باس شکست خورده است و در چرخهٔ بعدی بازمی‌گردد.',{'hp':boss.hp,'max_hp':boss.max_hp}
        since=datetime.utcnow()-timedelta(seconds=20)
        recent=await session.scalar(select(CharacterActivity.id).where(CharacterActivity.character_id==char.id,CharacterActivity.event_type=='world_boss_attack',CharacterActivity.created_at>=since).limit(1))
        if recent:return False,'برای جلوگیری از اسپم، هر ۲۰ ثانیه فقط یک حمله مجاز است.',{'hp':boss.hp,'max_hp':boss.max_hp}
        from services.character_stats_service import calculate_character_combat_stats
        stats=await calculate_character_combat_stats(char)
        damage=max(1,int(stats.attack*random.uniform(.8,1.2)+stats.magic_power*.35))
        damage=min(damage,boss.hp);boss.hp=max(0,boss.hp-damage)
        contrib=await session.scalar(select(WorldBossContribution).where(WorldBossContribution.boss_id==boss.id,WorldBossContribution.character_id==char.id).with_for_update())
        if contrib is None:contrib=WorldBossContribution(boss_id=boss.id,character_id=char.id,damage=0,attacks=0);session.add(contrib)
        contrib.damage+=damage;contrib.attacks+=1
        session.add(CharacterActivity(character_id=char.id,event_type='world_boss_attack',details=f'damage={damage}'))
        defeated=boss.hp<=0
        if defeated:
            boss.status='defeated';boss.ended_at=datetime.utcnow()
            rows=list((await session.scalars(select(WorldBossContribution).where(WorldBossContribution.boss_id==boss.id).with_for_update())).all())
            for c in rows:
                if c.rewarded:continue
                reward_gold=max(100,int(boss.reward_gold*(0.5+min(c.damage, boss.max_hp)/boss.max_hp)))
                owner=await session.scalar(select(Character).where(Character.id==c.character_id).with_for_update())
                if owner:
                    owner.gold+=reward_gold;c.rewarded=True
                    session.add(CharacterActivity(character_id=owner.id,event_type='world_boss_reward',details=f'gold={reward_gold};damage={c.damage}'))
                    setting=await session.scalar(select(PlayerSetting).where(PlayerSetting.telegram_id==owner.telegram_id))
                    if setting is None or setting.notifications:
                        session.add(NotificationEvent(telegram_id=owner.telegram_id,event_type='world_boss_reward',message=f'🏆 پاداش یورش باس جهانی: {reward_gold:,} Gold و مشارکت {c.damage:,} آسیب',delivered=False))
        await session.commit()
        result={'hp':boss.hp,'max_hp':boss.max_hp,'damage':damage,'defeated':defeated}
    if result['defeated']:
        async with AsyncSessionLocal() as session:
            rows=list((await session.scalars(select(WorldBossContribution).where(WorldBossContribution.boss_id==boss.id))).all())
            for c in rows:
                await add_character_xp_for_character_id(c.character_id,boss.reward_xp)
    return True,f"به باس {damage:,} آسیب زدی!",result

async def add_character_xp_for_character_id(character_id:int,xp:int):
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.id==character_id))
        if char:tid=char.telegram_id
        else:return
    await add_character_xp(tid,xp)

async def list_market():
    async with AsyncSessionLocal() as session:
        rows=(await session.execute(select(MarketListing).where(MarketListing.status=='active').order_by(MarketListing.created_at.desc()).limit(20))).scalars().all()
        result=[]
        for row in rows:
            model=Item if row.item_kind=='item' else None
            if model is Item: obj=await session.scalar(select(Item).where(Item.id==row.item_id))
            else:
                from models.equipment import Equipment
                obj=await session.scalar(select(Equipment).where(Equipment.id==row.item_id))
            if obj: result.append((row,obj))
        return result

async def buy_market_listing(telegram_id:int,listing_id:int):
    async with AsyncSessionLocal() as session:
        buyer=await session.scalar(select(Character).where(Character.telegram_id==telegram_id).with_for_update())
        listing=await session.scalar(select(MarketListing).where(MarketListing.id==listing_id,MarketListing.status=='active').with_for_update())
        if not buyer or not listing:return False,'آگهی پیدا نشد.'
        if listing.seller_telegram_id==telegram_id:return False,'نمی‌توانی آگهی خودت را بخری.'
        total=listing.unit_price*listing.quantity
        if buyer.gold<total:return False,'Gold کافی نداری.'
        seller=await session.scalar(select(Character).where(Character.telegram_id==listing.seller_telegram_id).with_for_update())
        if not seller:return False,'فروشنده پیدا نشد.'
        if listing.item_kind=='item':
            inv=await session.scalar(select(Inventory).join(Character,Character.id==Inventory.character_id).where(Character.telegram_id==telegram_id,Inventory.item_id==listing.item_id).with_for_update())
            if inv is None:session.add(Inventory(character_id=buyer.id,item_id=listing.item_id,quantity=listing.quantity))
            else:inv.quantity+=listing.quantity
        else:
            from models.equipment import CharacterEquipment
            inv=await session.scalar(select(CharacterEquipment).where(CharacterEquipment.character_id==buyer.id,CharacterEquipment.equipment_id==listing.item_id).with_for_update())
            if inv is None:session.add(CharacterEquipment(character_id=buyer.id,equipment_id=listing.item_id,quantity=listing.quantity,equipped=False))
            else:inv.quantity+=listing.quantity
        buyer.gold-=total;seller.gold+=total;listing.status='sold'
        session.add(CharacterActivity(character_id=buyer.id,event_type='market_buy',details=f'listing={listing.id};total={total}'))
        session.add(CharacterActivity(character_id=seller.id,event_type='market_sale',details=f'listing={listing.id};total={total}'))
        await session.commit()
        return True,f'خرید انجام شد؛ {total:,} Gold پرداخت شد.'

async def create_market_listing(telegram_id:int,item_id:int,quantity:int,unit_price:int,item_kind:str='item'):
    from models.equipment import Equipment, CharacterEquipment
    if item_kind not in {'item','equipment'}:return False,'نوع آیتم معتبر نیست.'
    if not (1<=quantity<=1000 and 1<=unit_price<=10_000_000):return False,'تعداد یا قیمت معتبر نیست.'
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id).with_for_update())
        if not char:return False,'قهرمان پیدا نشد.'
        if item_kind=='item':
            item=await session.scalar(select(Item).where(Item.id==item_id,Item.is_tradeable.is_(True)))
            if not item:return False,'آیتم قابل معامله پیدا نشد.'
            inv=await session.scalar(select(Inventory).where(Inventory.character_id==char.id,Inventory.item_id==item.id).with_for_update())
        else:
            item=await session.scalar(select(Equipment).where(Equipment.id==item_id,Equipment.is_active.is_(True)))
            if not item:return False,'تجهیز قابل معامله پیدا نشد.'
            inv=await session.scalar(select(CharacterEquipment).where(CharacterEquipment.character_id==char.id,CharacterEquipment.equipment_id==item.id,CharacterEquipment.equipped.is_(False)).with_for_update())
        if not inv or inv.quantity<quantity:return False,'موجودی قابل فروش کافی نیست؛ تجهیزات پوشیده‌شده قابل فروش نیستند.'
        inv.quantity-=quantity
        if inv.quantity==0:await session.delete(inv)
        listing=MarketListing(seller_telegram_id=telegram_id,item_kind=item_kind,item_id=item.id,quantity=quantity,unit_price=unit_price,status='active');session.add(listing)
        session.add(CharacterActivity(character_id=char.id,event_type='market_list',details=f'kind={item_kind};item={item.id};quantity={quantity};price={unit_price}'))
        await session.commit()
        return True,f'آگهی #{listing.id} ثبت شد.'


async def create_equipment_market_listing(telegram_id:int,equipment_id:int,quantity:int,unit_price:int):
    """List unequipped owned equipment on the player market atomically."""
    from models.equipment import Equipment, CharacterEquipment
    if not (1 <= quantity <= 1000 and 1 <= unit_price <= 10_000_000):
        return False, 'تعداد یا قیمت معتبر نیست.'
    async with AsyncSessionLocal() as session:
        char = await session.scalar(select(Character).where(Character.telegram_id == telegram_id).with_for_update())
        if not char:
            return False, 'قهرمان پیدا نشد.'
        equipment = await session.scalar(select(Equipment).where(Equipment.id == equipment_id, Equipment.is_active.is_(True)))
        owned = await session.scalar(select(CharacterEquipment).where(
            CharacterEquipment.character_id == char.id,
            CharacterEquipment.equipment_id == equipment_id,
            CharacterEquipment.quantity > 0,
        ).with_for_update())
        if not equipment or not owned:
            return False, 'این تجهیز در صندوقچه‌ات وجود ندارد.'
        if owned.equipped:
            return False, 'ابتدا این تجهیز را از تن قهرمان خارج کن.'
        if int(owned.enhancement_level or 0) > 0:
            return False, 'تجهیز ارتقایافته قابل فروش نیست؛ ابتدا از تجهیز بدون ارتقا استفاده کن تا سطح ارتقا از بین نرود.'
        if owned.quantity < quantity:
            return False, f'تعداد موجودی کافی نیست؛ موجودی: {owned.quantity}.'
        owned.quantity -= quantity
        if owned.quantity <= 0:
            await session.delete(owned)
        listing = MarketListing(
            seller_telegram_id=telegram_id,
            item_kind='equipment',
            item_id=equipment.id,
            quantity=quantity,
            unit_price=unit_price,
            status='active',
        )
        session.add(listing)
        session.add(CharacterActivity(character_id=char.id, event_type='market_list', details=f'equipment={equipment.id};quantity={quantity};price={unit_price}'))
        await session.commit()
        return True, f'آگهی تجهیز «{equipment.name}» با شناسهٔ #{listing.id} ثبت شد.'

async def get_inventory_equipment_ids(telegram_id:int):
    from models.equipment import Equipment, CharacterEquipment
    async with AsyncSessionLocal() as session:
        char = await session.scalar(select(Character).where(Character.telegram_id == telegram_id))
        if not char:
            return []
        return (await session.execute(
            select(CharacterEquipment, Equipment)
            .join(Equipment, Equipment.id == CharacterEquipment.equipment_id)
            .where(CharacterEquipment.character_id == char.id, CharacterEquipment.quantity > 0, Equipment.is_active.is_(True))
            .order_by(Equipment.name)
        )).all()


async def evolve_active_pet(telegram_id:int):
    """شروع آموزش یک‌ساعتهٔ پت؛ XP فقط بعد از تکمیل آموزش اعطا می‌شود."""
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id).with_for_update())
        if not char:return False,'قهرمان پیدا نشد.'
        petrow=await session.scalar(select(CharacterPet).where(CharacterPet.character_id==char.id,CharacterPet.active.is_(True)).with_for_update())
        if not petrow:return False,'ابتدا یک پت را فعال کن.'
        pet=await session.scalar(select(Pet).where(Pet.id==petrow.pet_id))
        if not pet:return False,'پت پیدا نشد.'
        now=datetime.utcnow()
        if petrow.last_training_at:
            ready_at=petrow.last_training_at+timedelta(hours=1)
            if now < ready_at:
                remaining=max(0,int((ready_at-now).total_seconds()))
                minutes,seconds=divmod(remaining,60)
                status='در حال آموزش' if petrow.training_completed_at is None else 'برای تمرین دوباره آماده نیست'
                return False,f'🐾 پت شما {status} است؛ {minutes} دقیقه و {seconds} ثانیه باقی مانده است.'
            if petrow.training_completed_at is None:
                return False,'⏳ آموزش به پایان رسیده و نتیجه در حال ثبت است؛ چند ثانیه دیگر دوباره تلاش کن.'
        if petrow.level>=10:return False,'پت به حداکثر سطح فعلی رسیده است.'
        cost=petrow.level*500
        if char.gold<cost:return False,f'برای شروع آموزش به {cost:,} گلد نیاز داری.'
        char.gold-=cost
        petrow.last_training_at=now
        petrow.training_completed_at=None
        petrow.training_notified_at=None
        petrow.training_start_level=int(petrow.level or 1)
        session.add(CharacterActivity(character_id=char.id,event_type='pet_training_started',details=f'pet={pet.id};xp=100;cost={cost}'))
        await session.commit()
        return True,f'🐾 پت «{pet.name}» وارد وضعیت «در حال آموزش» شد. مدت آموزش دقیقاً ۱ ساعت است؛ پس از پایان، ۱۰۰ XP دریافت می‌کند و نتیجه در پیام خصوصی ارسال می‌شود.'


async def upgrade_equipment(telegram_id:int, equipment_id:int):
    from models.equipment import Equipment, CharacterEquipment
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id).with_for_update())
        if not char:return False,'قهرمان پیدا نشد.'
        owned=await session.scalar(select(CharacterEquipment).where(CharacterEquipment.character_id==char.id,CharacterEquipment.equipment_id==equipment_id,CharacterEquipment.quantity>0).with_for_update())
        equipment=await session.scalar(select(Equipment).where(Equipment.id==equipment_id,Equipment.is_active.is_(True)))
        if not owned or not equipment:return False,'این تجهیز در صندوقچه‌ات نیست.'
        level=int(owned.enhancement_level or 0)
        if level>=10:return False,'این تجهیز به حداکثر ارتقای +10 رسیده است.'
        if char.level < equipment.required_level:return False,'سطح قهرمان برای این تجهیز کافی نیست.'
        cost=500*(level+1)*(level+1)
        material_name,material_qty = (('🌿 گیاه اِلدوریا',1) if level < 3 else ('⛏️ تکه‌آهن گابلین',2) if level < 6 else ('💎 خرده‌سنگ جادویی',2) if level < 8 else ('🔥 فلس اژدها',1))
        if char.gold<cost:return False,f'برای ارتقا به {cost:,} Gold نیاز داری.'
        material=await session.scalar(select(Item).where(Item.name==material_name).limit(1))
        inv=await session.scalar(select(Inventory).where(Inventory.character_id==char.id,Inventory.item_id==material.id).with_for_update()) if material else None
        if inv is None or inv.quantity<material_qty:return False,f'برای این ارتقا به {material_name} ×{material_qty} نیاز داری.'
        inv.quantity-=material_qty
        if inv.quantity<=0: await session.delete(inv)
        char.gold-=cost;owned.enhancement_level=level+1
        session.add(CharacterActivity(character_id=char.id,event_type='upgrade',details=f'equipment={equipment.id};level={owned.enhancement_level};material={material_name}x{material_qty}'))
        await _progress_daily(session,char.id,'upgrade',1)
        await session.commit()
        return True,f'✨ {equipment.name} به +{owned.enhancement_level} ارتقا یافت. هزینه: {cost:,} Gold.'

async def queue_notification(telegram_id:int,event_type:str,message:str):
    async with AsyncSessionLocal() as session:
        setting=await session.scalar(select(PlayerSetting).where(PlayerSetting.telegram_id==telegram_id))
        if setting is not None and not setting.notifications:return
        session.add(NotificationEvent(telegram_id=telegram_id,event_type=event_type,message=message[:2000],delivered=False))
        await session.commit()

async def get_notifications(telegram_id:int):
    async with AsyncSessionLocal() as session:
        return list((await session.scalars(select(NotificationEvent).where(NotificationEvent.telegram_id==telegram_id).order_by(NotificationEvent.created_at.desc()).limit(15))).all())

async def mark_notifications_read(telegram_id:int):
    async with AsyncSessionLocal() as session:
        rows=list((await session.scalars(select(NotificationEvent).where(NotificationEvent.telegram_id==telegram_id,NotificationEvent.delivered.is_(False)))).all())
        for row in rows: row.delivered=True
        await session.commit()
        return len(rows)

async def cancel_market_listing(telegram_id:int,listing_id:int):
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id).with_for_update())
        listing=await session.scalar(select(MarketListing).where(MarketListing.id==listing_id,MarketListing.status=='active').with_for_update())
        if not char or not listing:return False,'آگهی فعال پیدا نشد.'
        if listing.seller_telegram_id!=telegram_id:return False,'فقط فروشنده می‌تواند آگهی را لغو کند.'
        if listing.item_kind=='item':
            inv=await session.scalar(select(Inventory).where(Inventory.character_id==char.id,Inventory.item_id==listing.item_id).with_for_update())
            if inv is None:session.add(Inventory(character_id=char.id,item_id=listing.item_id,quantity=listing.quantity))
            else:inv.quantity+=listing.quantity
        else:
            from models.equipment import CharacterEquipment
            inv=await session.scalar(select(CharacterEquipment).where(CharacterEquipment.character_id==char.id,CharacterEquipment.equipment_id==listing.item_id).with_for_update())
            if inv is None:session.add(CharacterEquipment(character_id=char.id,equipment_id=listing.item_id,quantity=listing.quantity,equipped=False))
            else:inv.quantity+=listing.quantity
        listing.status='cancelled'
        session.add(CharacterActivity(character_id=char.id,event_type='market_cancel',details=f'listing={listing.id}'))
        await session.commit()
        return True,'آگهی لغو شد و آیتم‌ها به صندوقچه برگشتند.'


async def update_market_listing_price(telegram_id: int, listing_id: int, unit_price: int):
    """Update the unit price of an active listing owned by this player."""
    if not 1 <= int(unit_price) <= 10_000_000:
        return False, 'قیمت باید بین ۱ تا ۱۰٬۰۰۰٬۰۰۰ گلد باشد.'
    async with AsyncSessionLocal() as session:
        listing = await session.scalar(
            select(MarketListing).where(
                MarketListing.id == listing_id,
                MarketListing.status == 'active',
            ).with_for_update()
        )
        if listing is None:
            return False, 'آگهی فعال پیدا نشد.'
        if listing.seller_telegram_id != telegram_id:
            return False, 'فقط صاحب آگهی اجازهٔ ویرایش آن را دارد.'
        listing.unit_price = int(unit_price)
        char = await session.scalar(select(Character).where(Character.telegram_id == telegram_id))
        if char:
            session.add(CharacterActivity(character_id=char.id, event_type='market_edit', details=f'listing={listing.id};price={unit_price}'))
        await session.commit()
        return True, f'قیمت آگهی #{listing.id} به {unit_price:,} گلد برای هر عدد تغییر کرد.'

async def get_owned_market_listings(telegram_id:int):
    async with AsyncSessionLocal() as session:
        return list((await session.scalars(select(MarketListing).where(MarketListing.seller_telegram_id==telegram_id,MarketListing.status=='active').order_by(MarketListing.created_at.desc()).limit(20))).all())

async def get_inventory_item_ids(telegram_id:int):
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id))
        if not char:return []
        rows=(await session.execute(select(Inventory,Item).join(Item,Item.id==Inventory.item_id).where(Inventory.character_id==char.id,Inventory.quantity>0,Item.is_tradeable.is_(True)).order_by(Item.name))).all()
        return rows


async def get_inventory_equipment_ids(telegram_id:int):
    from models.equipment import Equipment, CharacterEquipment
    async with AsyncSessionLocal() as session:
        char=await session.scalar(select(Character).where(Character.telegram_id==telegram_id))
        if not char:return []
        return list((await session.execute(select(CharacterEquipment,Equipment).join(Equipment,Equipment.id==CharacterEquipment.equipment_id).where(CharacterEquipment.character_id==char.id,CharacterEquipment.quantity>0,CharacterEquipment.equipped.is_(False)).order_by(Equipment.name))).all())
