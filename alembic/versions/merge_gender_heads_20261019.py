"""Merge the two historical character-gender migration branches."""
from alembic import op

revision = "merge_gender_heads_20261019"
down_revision = ("g4e5f6a7b8c9", "a1b2c3d4e5f6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Both parents only add the same optional gender column, guarded by inspection.
    pass


def downgrade() -> None:
    # A merge revision has no schema operation to reverse.
    pass
