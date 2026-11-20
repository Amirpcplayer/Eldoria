"""Add pet PvP command settings and 24-hour usage tracking."""
from alembic import op
import sqlalchemy as sa

revision = "ef71a2b3c4d5"
down_revision = "c91e2f7a6b40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("character_pets"):
        return
    columns = {c["name"] for c in inspector.get_columns("character_pets")}
    if "pet_attack_phrase" not in columns:
        op.add_column("character_pets", sa.Column("pet_attack_phrase", sa.String(length=32), nullable=True))
    if "pet_attack_uses" not in columns:
        op.add_column("character_pets", sa.Column("pet_attack_uses", sa.Integer(), nullable=False, server_default="0"))
    if "pet_attack_window_started_at" not in columns:
        op.add_column("character_pets", sa.Column("pet_attack_window_started_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("character_pets"):
        return
    columns = {c["name"] for c in inspector.get_columns("character_pets")}
    for name in ("pet_attack_window_started_at", "pet_attack_uses", "pet_attack_phrase"):
        if name in columns:
            op.drop_column("character_pets", name)
