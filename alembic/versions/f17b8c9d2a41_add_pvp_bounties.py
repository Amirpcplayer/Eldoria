"""Add escrowed PvP bounties."""
from alembic import op
import sqlalchemy as sa

revision = "f17b8c9d2a41"
down_revision = "ef71a2b3c4d5"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("pvp_bounties"):
        return
    op.create_table(
        "pvp_bounties",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("target_character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sponsor_character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("claimed_by_character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
    )
    for col in ("target_character_id", "sponsor_character_id", "status", "claimed_by_character_id"):
        op.create_index(f"ix_pvp_bounties_{col}", "pvp_bounties", [col])

def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("pvp_bounties"):
        return
    op.drop_table("pvp_bounties")
