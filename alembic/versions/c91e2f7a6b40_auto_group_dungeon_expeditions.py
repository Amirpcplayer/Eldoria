"""Add automatic group dungeon expeditions and dungeon-only loot."""
from alembic import op
import sqlalchemy as sa

revision = "c91e2f7a6b40"
down_revision = ("7f8e9a0b1c2d", "f4c8d2e6a901")
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "group_dungeon_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("chat_title", sa.String(255), nullable=False, server_default="گروه اِلدوریا"),
        sa.Column("dungeon_key", sa.String(64), nullable=False, server_default="zareth_catacombs"),
        sa.Column("dungeon_name", sa.String(120), nullable=False, server_default="مقبره‌های زارِث"),
        sa.Column("difficulty", sa.String(24), nullable=False, server_default="I"),
        sa.Column("recommended_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("spawned_at", sa.DateTime(), nullable=True),
        sa.Column("next_spawn_at", sa.DateTime(), nullable=False),
        sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="SET NULL"), nullable=True),
        sa.Column("leader_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("members_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("ready_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("ready_deadline", sa.DateTime(), nullable=True),
        sa.Column("run_started_at", sa.DateTime(), nullable=True),
        sa.Column("finishes_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_group_dungeon_events_chat_id", "group_dungeon_events", ["chat_id"])
    op.create_index("ix_group_dungeon_events_status", "group_dungeon_events", ["status"])
    op.create_index("ix_group_dungeon_events_next_spawn_at", "group_dungeon_events", ["next_spawn_at"])
    op.create_index("ix_group_dungeon_events_party_id", "group_dungeon_events", ["party_id"])
    op.create_table(
        "dungeon_loot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("item_key", sa.String(80), nullable=False),
        sa.Column("item_name", sa.String(120), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_gold", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("telegram_id", "item_key", name="uq_dungeon_loot_player_item"),
    )
    op.create_index("ix_dungeon_loot_telegram_id", "dungeon_loot", ["telegram_id"])

def downgrade() -> None:
    op.drop_index("ix_dungeon_loot_telegram_id", table_name="dungeon_loot")
    op.drop_table("dungeon_loot")
    op.drop_index("ix_group_dungeon_events_party_id", table_name="group_dungeon_events")
    op.drop_index("ix_group_dungeon_events_next_spawn_at", table_name="group_dungeon_events")
    op.drop_index("ix_group_dungeon_events_status", table_name="group_dungeon_events")
    op.drop_index("ix_group_dungeon_events_chat_id", table_name="group_dungeon_events")
    op.drop_table("group_dungeon_events")
