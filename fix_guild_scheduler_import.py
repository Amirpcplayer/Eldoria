from pathlib import Path
from datetime import datetime
import re

path = Path('main.py')
if not path.is_file():
    raise SystemExit('ERROR: main.py پیدا نشد. این فایل را از ریشه پروژه اجرا کن.')

text = path.read_text(encoding='utf-8')
original = text

# Remove only the stale import and task references that point to a missing function.
text = re.sub(r'(?m)^from services\.guild_service import guild_sale_payout_scheduler\s*\n', '', text)
text = re.sub(r'(?m)^\s*guild_sale_task\s*=\s*asyncio\.create_task\(guild_sale_payout_scheduler\(\),\s*name=["\']guild-sale-payout["\']\)\s*\n', '', text)
# Remove guild_sale_task from shutdown tuples, preserving the remaining task list.
text = re.sub(r',\s*guild_sale_task(?=\s*\))', '', text)
text = re.sub(r'(?<=\()\s*guild_sale_task\s*,\s*', '', text)

if text == original:
    if 'guild_sale_payout_scheduler' not in text:
        print('No change needed: main.py has no stale guild scheduler references.')
        raise SystemExit(0)
    raise SystemExit('ERROR: اشاره‌های scheduler پیدا شدند، اما الگوی امن اصلاح با ساختار فایل مطابقت نداشت؛ فایل دست‌نخورده ماند.')

backup = path.with_name(f'main.py.backup_guild_scheduler_{datetime.now():%Y%m%d_%H%M%S}')
backup.write_text(original, encoding='utf-8')
path.write_text(text, encoding='utf-8', newline='')
print(f'OK: اصلاح شد: {path}')
print(f'Backup: {backup}')
print('توجه: این اصلاح فقط خطای شروع ربات را رفع می‌کند؛ سیستم فروش آیتم به گیلد و واریز ۱۰٪ باید جداگانه پیاده‌سازی/تکمیل شود.')
