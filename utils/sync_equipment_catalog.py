"""Add the 36 requested shop entries without modifying legacy gear or player ownership.
Run once with the bot stopped: python -m utils.sync_equipment_catalog
"""
import asyncio
from sqlalchemy import select
from database.database import AsyncSessionLocal
from models.equipment import Equipment

SLOTS = [('weapon','سلاح'),('armor','زره'),('helmet','کلاه'),('boots','کفش'),('ring','انگشتر'),('necklace','گردنبند')]
TIERS = [
    ('آهنی','gold',1000,1,1), ('فولادی','gold',6000,30,3), ('کریستالی','gold',15000,60,7),
    ('اهریمنی','gem',300,70,12), ('الهی','gem',850,85,24), ('اِلدوریایی','gem',1500,100,42),
]
# Fixed prices by tier, each slot has its own appropriate base stats.
async def main():
    created = 0
    async with AsyncSessionLocal() as session:
        for tier,currency,price,level,power in TIERS:
            for slot,label in SLOTS:
                name=f'{tier} {label} اِلدوریا'
                existing=await session.scalar(select(Equipment.id).where(Equipment.name==name))
                if existing is not None: continue
                offensive = slot in ('weapon','ring','necklace')
                defensive = slot in ('armor','helmet','boots')
                session.add(Equipment(
                    name=name, description=f'تجهیز {tier}؛ {label} از آرشیو اِلدوریا.',
                    equipment_type=slot, rarity='common', required_level=level,
                    shop_price=price if currency=='gold' else 0,
                    gem_price=price if currency=='gem' else 0,
                    attack=power*(130 if slot=='weapon' else 25 if offensive else 8),
                    magic_power=power*(110 if slot=='weapon' else 30 if offensive else 8),
                    defense=power*(110 if defensive else 20),
                    magic_defense=power*(90 if defensive else 20),
                    hp=power*(1500 if defensive else 250),
                    mana=power*(300 if offensive else 120),
                    speed=power*(12 if slot=='boots' else 2),
                    accuracy=power*(8 if offensive else 2), critical=power*(2 if slot=='weapon' else 1),
                    is_active=True,
                ))
                created+=1
        await session.commit()
    print(f'Equipment catalog: {created} new entries; existing entries and player inventories unchanged.')

if __name__=='__main__': asyncio.run(main())
