"""Add shared guild inventory for material purchases from members."""
from alembic import op
import sqlalchemy as sa

revision = "guild_inventory_sales_20261019"
down_revision = "social_recovery_20261019"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "guild_inventories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("guild_id", sa.Integer(), sa.ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("guild_id", "item_id", name="uq_guild_inventory_item"),
    )
    op.create_index("ix_guild_inventories_guild_id", "guild_inventories", ["guild_id"])
    op.create_index("ix_guild_inventories_item_id", "guild_inventories", ["item_id"])

def downgrade() -> None:
    op.drop_index("ix_guild_inventories_item_id", table_name="guild_inventories")
    op.drop_index("ix_guild_inventories_guild_id", table_name="guild_inventories")
    op.drop_table("guild_inventories")
