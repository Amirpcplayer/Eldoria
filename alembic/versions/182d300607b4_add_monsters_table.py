"""add monsters table

Revision ID: 182d300607b4
Revises: bc90abd383a3
Create Date: 2026-10-06 08:08:57.608424

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "182d300607b4"
down_revision: Union[str, Sequence[str], None] = "bc90abd383a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create monsters table."""

    op.create_table(
        "monsters",

        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),

        # =====================================================
        # BASIC IDENTITY
        # =====================================================

        sa.Column(
            "family",
            sa.String(length=32),
            nullable=False,
        ),

        sa.Column(
            "variant",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        # =====================================================
        # POWER / TIER
        # =====================================================

        sa.Column(
            "tier",
            sa.String(length=32),
            nullable=False,
            server_default="normal",
        ),

        sa.Column(
            "power_multiplier",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),

        # =====================================================
        # ELEMENT
        # =====================================================

        sa.Column(
            "element",
            sa.String(length=32),
            nullable=False,
            server_default="neutral",
        ),

        # =====================================================
        # BASE STATS
        # =====================================================

        sa.Column(
            "base_hp",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),

        sa.Column(
            "base_attack",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),

        sa.Column(
            "base_magic_power",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),

        sa.Column(
            "base_defense",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),

        sa.Column(
            "base_magic_defense",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),

        sa.Column(
            "base_speed",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),

        sa.Column(
            "base_accuracy",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),

        sa.Column(
            "base_luck",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),

        sa.Column(
            "base_critical",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),

        # =====================================================
        # ELEMENT RESISTANCES
        # =====================================================

        sa.Column(
            "fire_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),

        sa.Column(
            "water_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),

        sa.Column(
            "ice_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),

        sa.Column(
            "earth_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),

        sa.Column(
            "wind_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),

        sa.Column(
            "electro_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),

        sa.Column(
            "shadow_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),

        sa.Column(
            "light_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),

        sa.Column(
            "blood_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),

        sa.Column(
            "steel_resistance",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),

        # =====================================================
        # STATUS
        # =====================================================

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        # =====================================================
        # CONSTRAINTS
        # =====================================================

        sa.PrimaryKeyConstraint(
            "id",
            name="monsters_pkey",
        ),

        sa.UniqueConstraint(
            "variant",
            name="uq_monsters_variant",
        ),
    )

    # =========================================================
    # INDEXES
    # =========================================================

    op.create_index(
        "ix_monsters_family",
        "monsters",
        ["family"],
        unique=False,
    )

    op.create_index(
        "ix_monsters_variant",
        "monsters",
        ["variant"],
        unique=False,
    )

    op.create_index(
        "ix_monsters_tier",
        "monsters",
        ["tier"],
        unique=False,
    )

    op.create_index(
        "ix_monsters_element",
        "monsters",
        ["element"],
        unique=False,
    )

    op.create_index(
        "ix_monsters_is_active",
        "monsters",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Drop monsters table."""

    op.drop_index(
        "ix_monsters_is_active",
        table_name="monsters",
    )

    op.drop_index(
        "ix_monsters_element",
        table_name="monsters",
    )

    op.drop_index(
        "ix_monsters_tier",
        table_name="monsters",
    )

    op.drop_index(
        "ix_monsters_variant",
        table_name="monsters",
    )

    op.drop_index(
        "ix_monsters_family",
        table_name="monsters",
    )

    op.drop_table("monsters")