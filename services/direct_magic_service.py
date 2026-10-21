from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.redis import redis
from models.character import Character
from models.character_skill import CharacterSkill
from models.skill import Skill
from models.world_systems import CharacterActivity, PvpRating
from services.combat_service import has_active_battle
from services.death_service import ensure_character_alive
from services.direct_pvp_service import (
    _claim_bounties,
    _cooldown_key,
)
from services.equipment_service import get_final_character_stats
from services.pvp_service import _has_active_pvp
from services.skill_service import get_skill_mana_cost, get_skill_power
from services.damage_service import calculate_damage


async def direct_magic_attack(
    attacker_id: int,
    target_id: int,
    skill_id: int,
) -> dict[str, Any]:
    if attacker_id == target_id:
        return {"ok": False, "message": "❌ نمی‌توانی به خودت جادو بزنی."}

    alive, msg = await ensure_character_alive(attacker_id)
    if not alive:
        return {"ok": False, "message": msg}

    alive, msg = await ensure_character_alive(target_id)
    if not alive:
        if "پیدا نشد" in msg:
            return {"ok": False, "message": "❌ بازیکن هدف هنوز شخصیت اِلدوریا نساخته است."}
        return {"ok": False, "message": "🛡️ بازیکن هدف فعلاً قابل حمله نیست. " + msg}

    if await has_active_battle(attacker_id) or await _has_active_pvp(attacker_id):
        return {"ok": False, "message": "⚔️ تا پایان نبرد فعلی نمی‌توانی جادوی PvP اجرا کنی."}

    if await has_active_battle(target_id) or await _has_active_pvp(target_id):
        return {"ok": False, "message": "🛡️ این بازیکن در نبرد دیگری حضور دارد."}

    key = _cooldown_key(attacker_id, target_id)
    acquired = await redis.set(key, "1", nx=True, ex=10)
    if not acquired:
        ttl = max(1, int(await redis.ttl(key)))
        return {"ok": False, "message": f"⏳ برای حملهٔ دوباره {ttl} ثانیه صبر کن."}

    try:
        attacker_stats = await get_final_character_stats(attacker_id)
        target_stats = await get_final_character_stats(target_id)

        if not attacker_stats or not target_stats:
            await redis.delete(key)
            return {"ok": False, "message": "❌ دریافت مشخصات مبارزه ناموفق بود."}

        async with AsyncSessionLocal() as session:
            attacker = await session.scalar(
                select(Character)
                .where(Character.telegram_id == attacker_id)
                .with_for_update()
            )
            target = await session.scalar(
                select(Character)
                .where(Character.telegram_id == target_id)
                .with_for_update()
            )

            if attacker is None or target is None:
                await redis.delete(key)
                return {"ok": False, "message": "❌ هر دو بازیکن باید شخصیت ساخته باشند."}

            now = datetime.utcnow()
            if (
                (attacker.dead_until and attacker.dead_until > now)
                or (target.dead_until and target.dead_until > now)
            ):
                await redis.delete(key)
                return {"ok": False, "message": "💀 یکی از قهرمانان در دورهٔ احیاست."}

            pair = await session.execute(
                select(Skill, CharacterSkill)
                .join(CharacterSkill, CharacterSkill.skill_id == Skill.id)
                .where(
                    CharacterSkill.character_id == attacker.id,
                    CharacterSkill.skill_id == skill_id,
                    CharacterSkill.unlocked.is_(True),
                    CharacterSkill.level >= 1,
                    Skill.is_active.is_(True),
                )
            )
            result = pair.first()
            if not result:
                await redis.delete(key)
                return {"ok": False, "message": "❌ این جادو را یاد نگرفته‌ای یا در دسترس نیست."}

            skill, learned = result
            mana_cost = get_skill_mana_cost(skill, int(learned.level or 1))
            if int(attacker.mana or 0) < mana_cost:
                await redis.delete(key)
                return {
                    "ok": False,
                    "message": f"🔮 مانای کافی نداری؛ نیاز: {mana_cost}، مانای فعلی: {attacker.mana}.",
                }

            attacker.mana -= mana_cost

            magic_power = max(
                1,
                int(attacker_stats.get("magic_power", attacker.magic_power or 1)),
            )
            raw_power = max(
                1,
                int(get_skill_power(skill, int(learned.level or 1)) + magic_power * 0.7),
            )

            crit_chance = max(
                0,
                min(50, int(attacker_stats.get("critical", attacker.critical or 0))),
            )
            critical = random.randint(1, 100) <= crit_chance

            damage_result = calculate_damage(
                attack=raw_power,
                defense=max(
                    0,
                    int(target_stats.get("magic_defense", target.magic_defense or 0)),
                ),
                attack_element=str(skill.element or "neutral").lower(),
                defender_element="neutral",
                critical=critical,
                randomize=True,
            )
            damage = int(damage_result.damage)

            old_target_gold = max(0, int(target.gold or 0))
            attack_reward = min(500, max(0, damage) // 100)
            target.hp = max(0, int(target.hp or 0) - damage)
            killed = target.hp <= 0
            loot = min(2_000, old_target_gold, int(old_target_gold * 0.05)) if killed else 0

            attacker.gold = min(
                2_147_483_647,
                int(attacker.gold or 0) + attack_reward + loot,
            )

            bounty_reward = 0
            if killed:
                target.gold = max(0, old_target_gold - loot)
                target.dead_until = now + timedelta(minutes=10)

                bounty_reward = await _claim_bounties(
                    session, target.id, attacker.id, now
                )

                rating = await session.scalar(
                    select(PvpRating)
                    .where(PvpRating.character_id == attacker.id)
                    .with_for_update()
                )
                if rating is None:
                    rating = PvpRating(
                        character_id=attacker.id, rating=1000, wins=0, losses=0
                    )
                    session.add(rating)
                    await session.flush()
                rating.rating += 20
                rating.wins += 1
                rating.updated_at = now

                loser_rating = await session.scalar(
                    select(PvpRating)
                    .where(PvpRating.character_id == target.id)
                    .with_for_update()
                )
                if loser_rating is None:
                    loser_rating = PvpRating(
                        character_id=target.id, rating=1000, wins=0, losses=0
                    )
                    session.add(loser_rating)
                    await session.flush()
                loser_rating.rating = max(0, int(loser_rating.rating) - 10)
                loser_rating.losses += 1
                loser_rating.updated_at = now

                session.add(
                    CharacterActivity(
                        character_id=attacker.id,
                        event_type="pvp_win",
                        details=f"direct_magic;skill={skill.id};damage={damage};loot={loot}",
                    )
                )
                session.add(
                    CharacterActivity(
                        character_id=target.id,
                        event_type="pvp_loss",
                        details=f"direct_magic;skill={skill.id};damage={damage};loot_lost={loot}",
                    )
                )
            else:
                session.add(
                    CharacterActivity(
                        character_id=attacker.id,
                        event_type="pvp_attack",
                        details=f"direct_magic;target={target.id};skill={skill.id};damage={damage}",
                    )
                )

            await session.commit()
            return {
                "ok": True,
                "attacker_name": attacker.name,
                "target_name": target.name,
                "skill_name": skill.name,
                "skill_element": skill.element,
                "mana_cost": mana_cost,
                "mana_left": int(attacker.mana or 0),
                "damage": damage,
                "critical": critical,
                "attacker_title": attacker.active_title or "شاگرد اِلدوریا",
                "target_title": target.active_title or "شاگرد اِلدوریا",
                "attacker_stats": attacker_stats,
                "target_stats": target_stats,
                "target_hp": int(target.hp or 0),
                "target_max_hp": max(1, int(target.max_hp or 100)),
                "attack_reward": attack_reward,
                "loot": loot,
                "killed": killed,
                "bounty_reward": bounty_reward,
            }

    except Exception:
        await redis.delete(key)
        raise
