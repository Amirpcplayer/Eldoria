"""Add gender to characters for character creation."""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f17b8c9d2a41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("characters")}
    if "gender" not in columns:
        op.add_column(
            "characters",
            sa.Column("gender", sa.String(length=16), nullable=False, server_default="male"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("characters"):
        columns = {column["name"] for column in sa.inspect(bind).get_columns("characters")}
        if "gender" in columns:
            op.drop_column("characters", "gender")
