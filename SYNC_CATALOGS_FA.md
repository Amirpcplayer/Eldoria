# همگام‌سازی کاتالوگ‌های World Eldoria در ویندوز

1. ربات را با `Ctrl+C` متوقف کنید.
2. از فایل `eldoria.db` نسخهٔ پشتیبان بگیرید.
3. در پوشهٔ اصلی پروژه، `sync_catalogs.bat` را اجرا کنید.
4. برای همگام‌سازی کامل گزینهٔ `1` را انتخاب کنید؛ برای همگام‌سازی یک بخش، گزینهٔ همان بخش را بزنید.
5. پس از نمایش `Catalog synchronization completed`، `run_game.bat` را اجرا کنید.

همین ابزار از خط فرمان نیز قابل اجراست:

```powershell
.\.venv\Scripts\python.exe sync_catalogs.py all
.\.venv\Scripts\python.exe sync_catalogs.py monsters
.\.venv\Scripts\python.exe sync_catalogs.py adventure
.\.venv\Scripts\python.exe sync_catalogs.py items
.\.venv\Scripts\python.exe sync_catalogs.py equipment
.\.venv\Scripts\python.exe sync_catalogs.py skills
.\.venv\Scripts\python.exe sync_catalogs.py quests
.\.venv\Scripts\python.exe sync_catalogs.py crafting
.\.venv\Scripts\python.exe sync_catalogs.py pets-events
.\.venv\Scripts\python.exe sync_catalogs.py fanart
```

## چه مواردی همگام می‌شوند؟

- هیولاها و گونه‌هایشان
- مناطق ماجراجویی و اتصال دشمنان به هیولاها
- آیتم‌ها و مواد
- تجهیزات پایه و رده‌های تکمیلی
- مهارت‌ها
- مأموریت‌ها (با آماده‌سازی پیش‌نیاز دشمن و مهارت)
- دستورهای ساخت و مواد لازم
- پت‌ها و رویداد آغازین
- بررسی کاتالوگ فن‌آرت و تعداد آیتم‌های فعال/غیرفعال، مالکیت‌ها و سفارش‌ها

این ابزار از seedهای موجود پروژه استفاده می‌کند و برای اجرای مجدد طراحی شده است. اطلاعات شخصیت‌ها و موجودی بازیکنان را حذف نمی‌کند؛ با این حال، قبل از همگام‌سازی از دیتابیس پشتیبان بگیرید و ربات را متوقف کنید.

نکتهٔ فن‌آرت: فن‌آرت اکنون در گزارش «ALL catalogs» و گزینهٔ ۱۰ بررسی می‌شود، اما خود آیتم‌ها باید از طرف ادمین با دستور `/fanart_add` در پی‌وی ربات ثبت شوند. هر آیتم به `file_id` واقعی عکس تلگرام نیاز دارد؛ بنابراین seed ساختگی یا عکس غیرواقعی تولید نمی‌شود. «فن‌آرت در کاتالوگ» با «مالکیت فن‌آرت توسط بازیکن» فرق دارد؛ بازیکن پس از خرید، شکار گروهی یا دریافت هدیه مالک آن می‌شود. نژادهای شخصیت در کد handler تعریف شده‌اند؛ اطلاعات بازار و پیشرفت‌های گیلد/سیاهچال هم داده‌های عملیاتی یا کاربرمحورند و بازسازی نمی‌شوند.
