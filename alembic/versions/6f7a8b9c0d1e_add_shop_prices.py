"""add shop prices

Revision ID: 6f7a8b9c0d1e
Revises: xxxx
Create Date: 2026-10-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f7a8b9c0d1e"
down_revision: Union[str, Sequence[str], None] = "2d3e4f5a6b7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column(
            "buy_price",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.add_column(
        "equipments",
        sa.Column(
            "shop_price",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # Existing shop catalogue.
    item_prices = {
        "🧪 معجون سلامتی": 100,
        "🧪 معجون سلامتی بزرگ": 250,
        "🗃 سنگ جادویی": 150,
        "📜 اسکرول قدرت": 300,
    }

    equipment_prices = {
        "⚔️ شمشیر آهنی": 500,
        "🔥 شمشیر شعله‌ای": 1500,
        "🪖 کلاه آهنی": 600,
        "🛡️ زره آهنی": 1200,
        "👢 چکمه مسافرتی": 800,
        "💍 انگشتر قدرت": 1000,
        "📿 گردنبند جادو": 1200,
    }

    for name, price in item_prices.items():
        op.execute(
            sa.text(
                "UPDATE items SET buy_price = :price WHERE name = :name"
            ).bindparams(
                price=price,
                name=name,
            )
        )

    for name, price in equipment_prices.items():
        op.execute(
            sa.text(
                "UPDATE equipments SET shop_price = :price WHERE name = :name"
            ).bindparams(
                price=price,
                name=name,
            )
        )

    op.alter_column("items", "buy_price", server_default=None)
    op.alter_column("equipments", "shop_price", server_default=None)


def downgrade() -> None:
    op.drop_column("equipments", "shop_price")
    op.drop_column("items", "buy_price")
