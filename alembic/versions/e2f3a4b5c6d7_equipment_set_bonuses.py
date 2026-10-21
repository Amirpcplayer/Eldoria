"""Add equipment set keys for shared combat-stat bonuses."""
from alembic import op
import sqlalchemy as sa

revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("equipments", sa.Column("set_key", sa.String(length=40), nullable=True))
    op.create_index("ix_equipments_set_key", "equipments", ["set_key"], unique=False)

def downgrade():
    op.drop_index("ix_equipments_set_key", table_name="equipments")
    op.drop_column("equipments", "set_key")
