"""Raise skill level cap and balance endgame stats."""
from alembic import op
import sqlalchemy as sa

revision = "d91c7f20a6b4"
down_revision = "ca72b1d4e9f0"
branch_labels = None
depends_on = None

def upgrade():
    op.execute(sa.text("UPDATE skills SET max_level = 200 WHERE max_level < 200"))
    op.execute(sa.text("UPDATE items SET description = 'حداقل ۵٬۰۰۰ HP یا ۱۰٪ از حداکثر HP قهرمان را بازیابی می‌کند.' WHERE name = '🧪 معجون سلامتی'"))
    op.execute(sa.text("UPDATE items SET description = 'حداقل ۲۵٬۰۰۰ HP یا ۲۵٪ از حداکثر HP قهرمان را بازیابی می‌کند.' WHERE name = '🧪 معجون سلامتی بزرگ'"))
    op.execute(sa.text("UPDATE items SET description = 'حداقل ۵٬۰۰۰ Mana یا ۱۰٪ از حداکثر Mana قهرمان را بازیابی می‌کند.' WHERE name IN ('🔷 معجون مانا', '🧪 معجون مانا')"))
    op.execute(sa.text("UPDATE items SET description = 'حداقل ۲۵٬۰۰۰ Mana یا ۲۵٪ از حداکثر Mana قهرمان را بازیابی می‌کند.' WHERE name IN ('🧪 معجون مانای بزرگ', '🔷 معجون مانای بزرگ')"))

def downgrade():
    op.execute(sa.text("UPDATE skills SET max_level = 10 WHERE max_level > 10"))
    op.execute(sa.text("UPDATE items SET description = '۴۰ واحد HP بازیابی می‌کند.' WHERE name = '🧪 معجون سلامتی'"))
    op.execute(sa.text("UPDATE items SET description = '۸۰ واحد HP بازیابی می‌کند.' WHERE name = '🧪 معجون سلامتی بزرگ'"))
