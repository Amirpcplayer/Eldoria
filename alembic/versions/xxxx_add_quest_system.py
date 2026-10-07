"""add quest system

Revision ID: xxxx
Revises: e3ab31677a52
Create Date: 2026-10-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ============================================================
# Revision identifiers
# ============================================================

revision: str = "xxxx"

down_revision: Union[str, Sequence[str], None] = "e3ab31677a52"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# Upgrade
# ============================================================

def upgrade() -> None:

    # --------------------------------------------------------
    # Quests
    # --------------------------------------------------------

    op.create_table(
        "quests",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),

        sa.Column(
            "name",
            sa.String(length=120),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "category",
            sa.String(length=32),
            nullable=False,
            server_default="story",
        ),

        sa.Column(
            "objective_type",
            sa.String(length=32),
            nullable=False,
        ),

        sa.Column(
            "target_id",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "required_amount",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),

        sa.Column(
            "min_level",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),

        sa.Column(
            "prerequisite_quest_id",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "reward_xp",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "reward_skill_xp",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "reward_gold",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "reward_equipment_id",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "is_repeatable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        # ----------------------------------------------------
        # Self prerequisite
        # ----------------------------------------------------

        sa.ForeignKeyConstraint(
            ["prerequisite_quest_id"],
            ["quests.id"],
        ),

        # ----------------------------------------------------
        # Equipment reward
        #
        # IMPORTANT:
        # Actual database table name is "equipments".
        # ----------------------------------------------------

        sa.ForeignKeyConstraint(
            ["reward_equipment_id"],
            ["equipments.id"],
        ),
    )

    # --------------------------------------------------------
    # Quest indexes
    # --------------------------------------------------------

    op.create_index(
        "ix_quests_category",
        "quests",
        ["category"],
    )

    op.create_index(
        "ix_quests_is_active",
        "quests",
        ["is_active"],
    )

    # --------------------------------------------------------
    # Character Quests
    # --------------------------------------------------------

    op.create_table(
        "character_quests",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),

        sa.Column(
            "character_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "quest_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "progress",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),

        sa.Column(
            "completed_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "claimed_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        # ----------------------------------------------------
        # Character relation
        # ----------------------------------------------------

        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
        ),

        # ----------------------------------------------------
        # Quest relation
        # ----------------------------------------------------

        sa.ForeignKeyConstraint(
            ["quest_id"],
            ["quests.id"],
        ),
    )

    # --------------------------------------------------------
    # Character Quest indexes
    # --------------------------------------------------------

    op.create_index(
        "ix_character_quests_character_id",
        "character_quests",
        ["character_id"],
    )

    op.create_index(
        "ix_character_quests_quest_id",
        "character_quests",
        ["quest_id"],
    )

    # --------------------------------------------------------
    # Prevent duplicate quest assignment
    # --------------------------------------------------------

    op.create_unique_constraint(
        "uq_character_quests_character_quest",
        "character_quests",
        [
            "character_id",
            "quest_id",
        ],
    )


# ============================================================
# Downgrade
# ============================================================

def downgrade() -> None:

    # --------------------------------------------------------
    # Character quests
    # --------------------------------------------------------

    op.drop_constraint(
        "uq_character_quests_character_quest",
        "character_quests",
        type_="unique",
    )

    op.drop_index(
        "ix_character_quests_quest_id",
        table_name="character_quests",
    )

    op.drop_index(
        "ix_character_quests_character_id",
        table_name="character_quests",
    )

    op.drop_table(
        "character_quests",
    )

    # --------------------------------------------------------
    # Quests
    # --------------------------------------------------------

    op.drop_index(
        "ix_quests_is_active",
        table_name="quests",
    )

    op.drop_index(
        "ix_quests_category",
        table_name="quests",
    )

    op.drop_table(
        "quests",
    )