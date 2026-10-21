from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class PlayerSetting(Base):
    __tablename__ = "player_settings"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(
        String(8), default="fa", nullable=False
    )
    notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    show_profile_fan_art_in_groups: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class Party(Base):
    __tablename__ = "parties"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    leader_telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(
        String(40), default="پارتی اِلدوریا", nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(40), default="ماجراجویان", nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text, default="", nullable=False
    )
    max_members: Mapped[int] = mapped_column(
        Integer, default=4, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), default="open", nullable=False, index=True
    )
    activity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank: Mapped[str] = mapped_column(String(4), default="F", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class PartyMember(Base):
    __tablename__ = "party_members"
    __table_args__ = (
        UniqueConstraint(
            "party_id",
            "telegram_id",
            name="uq_party_member",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False
    )
    tag: Mapped[str] = mapped_column(
        String(8), unique=True, nullable=False
    )
    owner_telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    max_members: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )
    level: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    xp: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    treasury_gold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sale_remainder: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_sale_gold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_sale_payout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    motto: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    emblem: Mapped[str] = mapped_column(String(16), default="🛡️", nullable=False)
    last_leader_reward_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class GuildMember(Base):
    __tablename__ = "guild_members"
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "telegram_id",
            name="uq_guild_member",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    guild_id: Mapped[int] = mapped_column(
        ForeignKey("guilds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(16), default="member", nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class DungeonRun(Base):
    __tablename__ = "dungeon_runs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    party_id: Mapped[int | None] = mapped_column(
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dungeon_key: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    floor: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), default="active", nullable=False, index=True
    )
    reward_gold: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class PvpChallenge(Base):
    __tablename__ = "pvp_challenges"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    challenger_telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    opponent_telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False, index=True
    )
    winner_telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class CraftRecipe(Base):
    __tablename__ = "craft_recipes"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(80), nullable=False
    )
    result_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("items.id"), nullable=True
    )
    result_equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipments.id"), nullable=True
    )
    gold_cost: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    materials_json: Mapped[str] = mapped_column(
        Text, default="{}", nullable=False
    )
    required_level: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    rarity: Mapped[str] = mapped_column(
        String(24), default="common", nullable=False
    )
    bonus_attack: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    bonus_defense: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    bonus_hp: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    price: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )


class CharacterPet(Base):
    __tablename__ = "character_pets"
    __table_args__ = (
        UniqueConstraint(
            "character_id",
            "pet_id",
            name="uq_character_pet",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pet_id: Mapped[int] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evolution_stage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_training_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    training_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    training_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    training_start_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pet_attack_phrase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pet_attack_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pet_attack_window_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )
    ends_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )
    reward_gold: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    reward_xp: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

class GroupDungeonState(Base):
    """Legacy shared-combat table retained for migration compatibility."""
    __tablename__ = "group_dungeon_states"
    __table_args__ = (UniqueConstraint("party_id", name="uq_group_dungeon_party"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    party_id: Mapped[int] = mapped_column(ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True)
    dungeon_key: Mapped[str] = mapped_column(String(32), nullable=False)
    floor: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    floor_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    enemy_name: Mapped[str] = mapped_column(String(80), nullable=False)
    enemy_hp: Mapped[int] = mapped_column(Integer, nullable=False)
    enemy_max_hp: Mapped[int] = mapped_column(Integer, nullable=False)
    members_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    actions_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    turn_started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class GroupDungeonEvent(Base):
    """One automatically spawned expedition slot per Telegram group."""
    __tablename__ = "group_dungeon_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    chat_title: Mapped[str] = mapped_column(String(255), default="گروه اِلدوریا", nullable=False)
    dungeon_key: Mapped[str] = mapped_column(String(64), default="zareth_catacombs", nullable=False)
    dungeon_name: Mapped[str] = mapped_column(String(120), default="مقبره‌های زارِث", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(24), default="I", nullable=False)
    recommended_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="waiting", nullable=False, index=True)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    spawned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_spawn_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    party_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id", ondelete="SET NULL"), nullable=True, index=True)
    leader_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    members_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    ready_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    ready_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    run_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finishes_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DungeonLoot(Base):
    """Dungeon-only collectible loot, never mixed with shop inventory."""
    __tablename__ = "dungeon_loot"
    __table_args__ = (UniqueConstraint("telegram_id", "item_key", name="uq_dungeon_loot_player_item"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    item_key: Mapped[str] = mapped_column(String(80), nullable=False)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_gold: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class GuildMaterial(Base):
    __tablename__ = "guild_materials"
    __table_args__ = (UniqueConstraint("guild_id", "item_id", name="uq_guild_material"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
