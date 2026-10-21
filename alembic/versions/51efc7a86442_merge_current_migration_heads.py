"""merge current migration heads

Revision ID: 51efc7a86442
Revises: guild_inventory_sales_20261019, guild_material_sales_20261021
Create Date: 2026-10-21 10:24:00.009171

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51efc7a86442'
down_revision: Union[str, Sequence[str], None] = ('guild_inventory_sales_20261019', 'guild_material_sales_20261021')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
