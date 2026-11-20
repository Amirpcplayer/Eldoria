"""Add selected level to group boss slot."""
from alembic import op
import sqlalchemy as sa
revision = "ca72b1d4e9f0"
down_revision = "bc21dd32ee43"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.add_column("group_bosses", sa.Column("boss_level", sa.Integer(), nullable=False, server_default="1"))
def downgrade() -> None:
    op.drop_column("group_bosses", "boss_level")
