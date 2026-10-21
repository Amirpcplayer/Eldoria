"""Add persistent recovery and social progression fields."""
from alembic import op
import sqlalchemy as sa

revision = "social_recovery_20261019"
down_revision = "merge_gender_heads_20261019"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    if table not in sa.inspect(bind).get_table_names():
        return
    names = {item["name"] for item in sa.inspect(bind).get_columns(table)}
    if column.name not in names:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("characters", sa.Column("last_vitals_recovery_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("guilds", sa.Column("treasury_gold", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("guilds", sa.Column("description", sa.Text(), nullable=False, server_default=""))
    _add_column_if_missing("guilds", sa.Column("motto", sa.String(length=120), nullable=False, server_default=""))
    _add_column_if_missing("guilds", sa.Column("emblem", sa.String(length=16), nullable=False, server_default="🛡️"))
    _add_column_if_missing("guilds", sa.Column("last_leader_reward_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("parties", sa.Column("activity_score", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("parties", sa.Column("rank", sa.String(length=4), nullable=False, server_default="F"))


def downgrade() -> None:
    bind = op.get_bind()
    for table, columns in {
        "characters": ["last_vitals_recovery_at"],
        "guilds": ["treasury_gold", "description", "motto", "emblem", "last_leader_reward_at"],
        "parties": ["activity_score", "rank"],
    }.items():
        if table not in sa.inspect(bind).get_table_names():
            continue
        existing = {item["name"] for item in sa.inspect(bind).get_columns(table)}
        for column in columns:
            if column in existing:
                op.drop_column(table, column)
