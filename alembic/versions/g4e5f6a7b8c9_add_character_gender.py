"""Add optional character gender."""
from alembic import op
import sqlalchemy as sa

revision = "g4e5f6a7b8c9"
down_revision = "f17b8c9d2a41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("characters")}
    if "gender" not in columns:
        op.add_column("characters", sa.Column("gender", sa.String(length=16), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if "characters" in sa.inspect(bind).get_table_names():
        columns = {column["name"] for column in sa.inspect(bind).get_columns("characters")}
        if "gender" in columns:
            op.drop_column("characters", "gender")
