"""Guild material inventory and 24h sale rewards."""
from alembic import op
import sqlalchemy as sa
revision="guild_material_sales_20261021"
down_revision="social_recovery_20261019"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("guilds",sa.Column("pending_sale_gold",sa.Integer(),nullable=False,server_default="0"))
    op.add_column("guilds",sa.Column("sale_remainder",sa.Integer(),nullable=False,server_default="0"))
    op.add_column("guilds",sa.Column("next_sale_payout_at",sa.DateTime(),nullable=True))
    op.create_table("guild_materials",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("guild_id",sa.Integer(),sa.ForeignKey("guilds.id",ondelete="CASCADE"),nullable=False),sa.Column("item_id",sa.Integer(),sa.ForeignKey("items.id",ondelete="CASCADE"),nullable=False),sa.Column("quantity",sa.Integer(),nullable=False,server_default="0"),sa.UniqueConstraint("guild_id","item_id",name="uq_guild_material"))
    op.create_index("ix_guild_materials_guild_id","guild_materials",["guild_id"])

def downgrade():
    op.drop_index("ix_guild_materials_guild_id",table_name="guild_materials")
    op.drop_table("guild_materials")
    for field in ("next_sale_payout_at","sale_remainder","pending_sale_gold"): op.drop_column("guilds",field)
