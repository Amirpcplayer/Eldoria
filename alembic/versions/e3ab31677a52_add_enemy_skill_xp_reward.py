"""add enemy skill xp reward

Revision ID: e3ab31677a52
Revises: 9b26c438063d
Create Date: 2026-10-05
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e3ab31677a52"
down_revision: Union[str, Sequence[str], None] = "9b26c438063d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # skill_xp_reward قبلاً توسط Migration قبلی
    # به جدول adventure_enemies اضافه شده است.
    #
    # این Migration فقط داده‌های موجود را
    # با فرمول نهایی Skill XP هماهنگ می‌کند.

    op.execute(
        """
        UPDATE adventure_enemies
        SET skill_xp_reward = 25 + (level * 15)
        """
    )


def downgrade() -> None:
    # عمداً خالی است.
    #
    # ستون skill_xp_reward متعلق به Migration قبلی
    # یعنی 9b26c438063d است و نباید اینجا حذف شود.
    pass