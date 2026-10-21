from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database.database import Base

class WorldBoss(Base):
    __tablename__ = 'world_bosses'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    boss_key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_hp: Mapped[int] = mapped_column(Integer, nullable=False, default=100000)
    hp: Mapped[int] = mapped_column(Integer, nullable=False, default=100000)
    reward_gold: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    reward_xp: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='active', index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class WorldBossContribution(Base):
    __tablename__ = 'world_boss_contributions'
    __table_args__ = (UniqueConstraint('boss_id','character_id',name='uq_world_boss_character'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    boss_id: Mapped[int] = mapped_column(ForeignKey('world_bosses.id', ondelete='CASCADE'), nullable=False, index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey('characters.id', ondelete='CASCADE'), nullable=False, index=True)
    damage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attacks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rewarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class MarketListing(Base):
    __tablename__ = 'market_listings'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seller_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    item_kind: Mapped[str] = mapped_column(String(16), nullable=False) # item/equipment
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='active', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

class CharacterBestiary(Base):
    __tablename__ = 'character_bestiary'
    __table_args__ = (UniqueConstraint('character_id','monster_id',name='uq_bestiary_character_monster'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(ForeignKey('characters.id', ondelete='CASCADE'), nullable=False, index=True)
    monster_id: Mapped[int] = mapped_column(ForeignKey('monsters.id', ondelete='CASCADE'), nullable=False, index=True)
    kills: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_killed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

class CharacterActivity(Base):
    __tablename__ = 'character_activity'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(ForeignKey('characters.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    details: Mapped[str] = mapped_column(Text, nullable=False, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

class DailyTaskProgress(Base):
    __tablename__ = 'daily_task_progress'
    __table_args__ = (UniqueConstraint('character_id','task_key','task_date',name='uq_daily_task_progress'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(ForeignKey('characters.id', ondelete='CASCADE'), nullable=False, index=True)
    task_key: Mapped[str] = mapped_column(String(40), nullable=False)
    task_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claimed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class NotificationEvent(Base):
    __tablename__ = 'notification_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

class PvpRating(Base):
    __tablename__ = 'pvp_ratings'
    __table_args__ = (UniqueConstraint('character_id',name='uq_pvp_rating_character'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(ForeignKey('characters.id',ondelete='CASCADE'),nullable=False,index=True)
    rating: Mapped[int] = mapped_column(Integer,nullable=False,default=1000)
    wins: Mapped[int] = mapped_column(Integer,nullable=False,default=0)
    losses: Mapped[int] = mapped_column(Integer,nullable=False,default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime,nullable=False,default=datetime.utcnow)

class GroupBoss(Base):
    """One hourly world-boss slot per Telegram group."""
    __tablename__ = 'group_bosses'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    chat_title: Mapped[str] = mapped_column(String(255), nullable=False, default='گروه اِلدوریا')
    boss_key: Mapped[str] = mapped_column(String(64), nullable=False, default='ancient_dragon')
    name: Mapped[str] = mapped_column(String(100), nullable=False, default='اژدهای باستانی')
    boss_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_hp: Mapped[int] = mapped_column(Integer, nullable=False, default=500000)
    hp: Mapped[int] = mapped_column(Integer, nullable=False, default=500000)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='waiting', index=True)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    spawned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_spawn_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

class GroupBossContribution(Base):
    __tablename__ = 'group_boss_contributions'
    __table_args__ = (UniqueConstraint('boss_id', 'character_id', name='uq_group_boss_character'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    boss_id: Mapped[int] = mapped_column(ForeignKey('group_bosses.id', ondelete='CASCADE'), nullable=False, index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey('characters.id', ondelete='CASCADE'), nullable=False, index=True)
    damage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attacks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class GroupBossAttackCooldown(Base):
    """Persistent per-player cooldown for each individual group boss."""
    __tablename__ = "group_boss_attack_cooldowns"
    __table_args__ = (UniqueConstraint("boss_id", "telegram_id", name="uq_group_boss_player_cooldown"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    boss_id: Mapped[int] = mapped_column(ForeignKey("group_bosses.id", ondelete="CASCADE"), nullable=False, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    last_attack_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class PvpBounty(Base):
    """Escrowed gold bounty paid to the player who defeats the target."""
    __tablename__ = "pvp_bounties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    sponsor_character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    claimed_by_character_id: Mapped[int | None] = mapped_column(ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
