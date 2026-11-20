"""Add persistent shared group dungeon combat state."""
from alembic import op
import sqlalchemy as sa

revision = "a3d7e9f102bc"
down_revision = "9c41a7d6e2b0"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "group_dungeon_states",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dungeon_key", sa.String(length=32), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("floor_count", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("enemy_name", sa.String(length=80), nullable=False),
        sa.Column("enemy_hp", sa.Integer(), nullable=False),
        sa.Column("enemy_max_hp", sa.Integer(), nullable=False),
        sa.Column("members_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("actions_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("turn_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("turn_started_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("party_id", name="uq_group_dungeon_party"),
    )
    op.create_index("ix_group_dungeon_states_party_id", "group_dungeon_states", ["party_id"])
    op.create_index("ix_group_dungeon_states_status", "group_dungeon_states", ["status"])

def downgrade() -> None:
    op.drop_index("ix_group_dungeon_states_status", table_name="group_dungeon_states")
    op.drop_index("ix_group_dungeon_states_party_id", table_name="group_dungeon_states")
    op.drop_table("group_dungeon_states")
