import asyncio, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from datetime import datetime, timedelta
from database.database import AsyncSessionLocal
from models.social_systems import Pet, CraftRecipe, GameEvent
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as s:
        pets=[('🐺 گرگ اِلدوری','common',3,2,10,500),('🐉 اژدهای کوچک','rare',8,5,25,2500),('🦄 تک‌شاخ نورانی','epic',5,8,40,7000),('🔥 ققنوس جاودان','legendary',9,6,35,9000),('🐕 سگ جهنمی','epic',10,4,28,7500),('🌙 پلنگ سایه','rare',7,4,22,3500),('❄️ گریفین یخی','epic',8,7,32,8000),('⚡ رعدبال','rare',9,3,20,4500),('🌿 نگهبان جنگل','epic',6,9,45,6500),('🌌 اژدهای اختری','legendary',12,8,48,12000)]
        for name,rar,a,d,h,p in pets:
            if not await s.scalar(select(Pet).where(Pet.name==name)):s.add(Pet(name=name,rarity=rar,bonus_attack=a,bonus_defense=d,bonus_hp=h,price=p))
        now=datetime.utcnow()
        if not await s.scalar(select(GameEvent).where(GameEvent.name=='جشن آغاز اِلدوریا')):s.add(GameEvent(name='جشن آغاز اِلدوریا',description='یک رویداد آزمایشی برای نسخه اولیه.',starts_at=now-timedelta(days=1),ends_at=now+timedelta(days=30),reward_gold=1000,reward_xp=500))
        await s.commit(); print('Social systems seeded successfully.')
asyncio.run(main())
