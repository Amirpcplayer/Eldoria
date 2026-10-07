"""change telegram_id to bigint

Revision ID: bc90abd383a3
Revises: xxxx
Create Date: 2026-10-05 07:45:41.289577

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ============================================================
# Revision identifiers
# ============================================================

revision: str = "bc90abd383a3"

down_revision: Union[str, Sequence[str], None] = "xxxx"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# Upgrade
# ============================================================

def upgrade() -> None:
    """
    Change characters.telegram_id from PostgreSQL INTEGER
    to BIGINT.

    Existing data is preserved.
    """

    op.alter_column(
        "characters",
        "telegram_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


# ============================================================
# Downgrade
# ============================================================

def downgrade() -> None:
    """
    Revert characters.telegram_id from BIGINT to INTEGER.

    WARNING:
    This will fail if the database contains Telegram IDs
    outside the PostgreSQL INTEGER range.
    """

    op.alter_column(
        "characters",
        "telegram_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )