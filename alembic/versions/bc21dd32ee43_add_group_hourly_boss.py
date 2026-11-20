"""Add per-group hourly boss and contribution tracking."""
from alembic import op
import sqlalchemy as sa

revision = "bc21dd32ee43"
down_revision = "aa10bb20cc30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_bosses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("chat_title", sa.String(length=255), nullable=False, server_default="گروه اِلدوریا"),
        sa.Column("boss_key", sa.String(length=64), nullable=False, server_default="ancient_dragon"),
        sa.Column("name", sa.String(length=100), nullable=False, server_default="اژدهای باستانی"),
        sa.Column("max_hp", sa.Integer(), nullable=False, server_default="500000"),
        sa.Column("hp", sa.Integer(), nullable=False, server_default="500000"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="waiting"),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("spawned_at", sa.DateTime(), nullable=True),
        sa.Column("next_spawn_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_group_bosses_chat_id", "group_bosses", ["chat_id"], unique=True)
    op.create_index("ix_group_bosses_status", "group_bosses", ["status"])
    op.create_index("ix_group_bosses_next_spawn_at", "group_bosses", ["next_spawn_at"])
    op.create_table(
        "group_boss_contributions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("boss_id", sa.Integer(), sa.ForeignKey("group_bosses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("damage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attacks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("boss_id", "character_id", name="uq_group_boss_character"),
    )
    op.create_index("ix_group_boss_contributions_boss_id", "group_boss_contributions", ["boss_id"])
    op.create_index("ix_group_boss_contributions_character_id", "group_boss_contributions", ["character_id"])
    # Ensure /use_mana has shop-available consumables without duplicating existing rows.
    op.execute(sa.text("""
        INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at)
        SELECT '🧪 معجون مانا', 'بازیابی 100 واحد Mana در نبردهای گروهی و معمولی', 'potion', 'common', 25, 250, true, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون مانا')
    """))
    op.execute(sa.text("""
        INSERT INTO items (name, description, item_type, rarity, sell_price, buy_price, is_tradeable, created_at)
        SELECT '🧪 معجون مانای بزرگ', 'بازیابی 300 واحد Mana در نبردهای گروهی و معمولی', 'potion', 'rare', 80, 800, true, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (SELECT 1 FROM items WHERE name = '🧪 معجون مانای بزرگ')
    """))


def downgrade() -> None:
    op.drop_table("group_boss_contributions")
    op.drop_table("group_bosses")
