"""add skill xp

Revision ID: 9b26c438063d
Revises: a46b09cebf43
Create Date: 2026-10-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b26c438063d"
down_revision: Union[str, Sequence[str], None] = "a46b09cebf43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # Character Skill XP
    # ---------------------------------------------------------
    op.add_column(
        "characters",
        sa.Column(
            "skill_xp",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # ---------------------------------------------------------
    # Enemy Skill XP Reward
    # ---------------------------------------------------------
    op.add_column(
        "adventure_enemies",
        sa.Column(
            "skill_xp_reward",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # مقدار Skill XP دشمن‌های موجود
    # فرمول نهایی:
    # 25 + (level * 15)
    op.execute(
        """
        UPDATE adventure_enemies
        SET skill_xp_reward = 25 + (level * 15)
        """
    )

    # بعد از مقداردهی، server_default را حذف می‌کنیم
    # تا مقدار پیش‌فرض فقط در Migration استفاده شود.
    op.alter_column(
        "characters",
        "skill_xp",
        server_default=None,
    )

    op.alter_column(
        "adventure_enemies",
        "skill_xp_reward",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column(
        "adventure_enemies",
        "skill_xp_reward",
    )

    op.drop_column(
        "characters",
        "skill_xp",
    )