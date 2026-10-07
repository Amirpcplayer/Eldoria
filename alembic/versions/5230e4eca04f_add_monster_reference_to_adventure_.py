"""add monster reference to adventure enemies

Revision ID: 5230e4eca04f
Revises: 182d300607b4
Create Date: 2026-10-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5230e4eca04f"
down_revision: Union[str, Sequence[str], None] = "182d300607b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "adventure_enemies",
        sa.Column(
            "monster_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_adventure_enemies_monster_id",
        "adventure_enemies",
        ["monster_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_adventure_enemies_monster_id",
        "adventure_enemies",
        "monsters",
        ["monster_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_adventure_enemies_monster_id",
        "adventure_enemies",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_adventure_enemies_monster_id",
        table_name="adventure_enemies",
    )

    op.drop_column(
        "adventure_enemies",
        "monster_id",
    )