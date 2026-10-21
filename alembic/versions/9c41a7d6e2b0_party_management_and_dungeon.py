"""Add party metadata and party dungeon runs safely.

Revision ID: 9c41a7d6e2b0
Revises: fbbbaae023c6
"""

from alembic import op
import sqlalchemy as sa


revision = "9c41a7d6e2b0"
down_revision = "fbbbaae023c6"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(table_name)


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {
        column["name"]
        for column in inspector.get_columns(table_name)
    }


def _indexes(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {
        index["name"]
        for index in inspector.get_indexes(table_name)
    }


def _foreign_keys(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {
        fk["name"]
        for fk in inspector.get_foreign_keys(table_name)
        if fk.get("name")
    }


def upgrade() -> None:
    # اگر جدول‌ها وجود نداشته باشند، خطا را واضح اعلام کن.
    for table_name in ("parties", "dungeon_runs"):
        if not _table_exists(table_name):
            raise RuntimeError(
                f"Required table '{table_name}' does not exist. "
                "Check the earlier Alembic migrations."
            )

    # اطلاعات فعلی پارتی‌ها حفظ می‌شود.
    party_columns = _columns("parties")

    if "title" not in party_columns:
        op.add_column(
            "parties",
            sa.Column(
                "title",
                sa.String(length=40),
                nullable=False,
                server_default="ماجراجویان",
            ),
        )

    party_columns = _columns("parties")

    if "description" not in party_columns:
        op.add_column(
            "parties",
            sa.Column(
                "description",
                sa.Text(),
                nullable=False,
                server_default="",
            ),
        )

    # اتصال اجرای دانجن به پارتی
    dungeon_columns = _columns("dungeon_runs")

    if "party_id" not in dungeon_columns:
        op.add_column(
            "dungeon_runs",
            sa.Column(
                "party_id",
                sa.Integer(),
                nullable=True,
            ),
        )

    # ایندکس party_id
    expected_index = "ix_dungeon_runs_party_id"

    if expected_index not in _indexes("dungeon_runs"):
        op.create_index(
            expected_index,
            "dungeon_runs",
            ["party_id"],
            unique=False,
        )

    # کلید خارجی party_id به parties.id
    expected_fk = "fk_dungeon_runs_party_id_parties"

    if expected_fk not in _foreign_keys("dungeon_runs"):
        # اگر کلید خارجی معادل از قبل وجود دارد، تکراری نساز.
        inspector = sa.inspect(op.get_bind())
        matching_fk = any(
            fk.get("referred_table") == "parties"
            and fk.get("constrained_columns") == ["party_id"]
            and fk.get("referred_columns") == ["id"]
            for fk in inspector.get_foreign_keys("dungeon_runs")
        )

        if not matching_fk:
            op.create_foreign_key(
                expected_fk,
                "dungeon_runs",
                "parties",
                ["party_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    # این ستون‌ها ممکن است پیش از اجرای این migration وجود داشته باشند.
    # حذف خودکارشان می‌تواند به ساختار یا اطلاعات موجود آسیب بزند.
    # در نتیجه downgrade عمداً چیزی را حذف نمی‌کند.
    pass