"""add character stats

Revision ID: 2e7403617147
Revises: 1f92617fada6
Create Date: 2026-10-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2e7403617147"
down_revision: Union[str, Sequence[str], None] = "1f92617fada6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(
        "characters",
        sa.Column(
            "hp",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "max_hp",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "mana",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "max_mana",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "attack",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "magic_power",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "defense",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "magic_defense",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "speed",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "accuracy",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "luck",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
    )

    op.add_column(
        "characters",
        sa.Column(
            "critical",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
    )


def downgrade() -> None:

    op.drop_column("characters", "critical")
    op.drop_column("characters", "luck")
    op.drop_column("characters", "accuracy")
    op.drop_column("characters", "speed")
    op.drop_column("characters", "magic_defense")
    op.drop_column("characters", "defense")
    op.drop_column("characters", "magic_power")
    op.drop_column("characters", "attack")
    op.drop_column("characters", "max_mana")
    op.drop_column("characters", "mana")
    op.drop_column("characters", "max_hp")
    op.drop_column("characters", "hp")