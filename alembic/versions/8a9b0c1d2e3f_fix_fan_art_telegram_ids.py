"""fix fan art telegram ids to bigint"""

from alembic import op
import sqlalchemy as sa


revision = "8a9b0c1d2e3f"
down_revision = "7f8e9a0b1c2d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The original Fan Art migration created these columns with
    # a different schema state. Add telegram_id as BIGINT only
    # when it does not already exist.
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    orders_columns = {
        column["name"]
        for column in inspector.get_columns("fan_art_orders")
    }

    ownership_columns = {
        column["name"]
        for column in inspector.get_columns("fan_art_ownerships")
    }

    if "telegram_id" not in orders_columns:
        op.add_column(
            "fan_art_orders",
            sa.Column(
                "telegram_id",
                sa.BigInteger(),
                nullable=True,
            ),
        )

        # Existing orders cannot have a meaningful Telegram ID if
        # the old column did not exist. Keep the column nullable for
        # historical rows.
        op.create_index(
            "ix_fan_art_orders_telegram_id",
            "fan_art_orders",
            ["telegram_id"],
            unique=False,
        )

    else:
        op.alter_column(
            "fan_art_orders",
            "telegram_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )

    if "telegram_id" not in ownership_columns:
        op.add_column(
            "fan_art_ownerships",
            sa.Column(
                "telegram_id",
                sa.BigInteger(),
                nullable=True,
            ),
        )

        op.create_index(
            "ix_fan_art_ownerships_telegram_id",
            "fan_art_ownerships",
            ["telegram_id"],
            unique=False,
        )

    else:
        op.alter_column(
            "fan_art_ownerships",
            "telegram_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    orders_columns = {
        column["name"]
        for column in inspector.get_columns("fan_art_orders")
    }

    ownership_columns = {
        column["name"]
        for column in inspector.get_columns("fan_art_ownerships")
    }

    if "telegram_id" in orders_columns:
        op.drop_index(
            "ix_fan_art_orders_telegram_id",
            table_name="fan_art_orders",
        )
        op.drop_column(
            "fan_art_orders",
            "telegram_id",
        )

    if "telegram_id" in ownership_columns:
        op.drop_index(
            "ix_fan_art_ownerships_telegram_id",
            table_name="fan_art_ownerships",
        )
        op.drop_column(
            "fan_art_ownerships",
            "telegram_id",
        )