# ⚔️ World Eldoria

ربات نقش‌آفرینی فانتزی تلگرام با Python، aiogram 3، PostgreSQL و Redis. این مخزن شامل کد بازی، دارایی‌ها، مهاجرت‌های پایگاه داده و تست‌های موجود است. پیش از انتشار عمومی یا ارتقای نسخه، بخش «چک‌لیست انتشار» را بخوانید.

## پیش‌نیازها

- Windows 10/11 یا Linux پشتیبانی‌شده
- Python 3.12 (پیشنهادی)
- Docker Desktop / Docker Engine با Compose
- توکن ربات از BotFather
- شناسه عددی حساب مدیر

## راه‌اندازی مستقل ویندوز بدون Docker

برای اجرای حالت مستقل، از فایل `run_game.bat` استفاده کن. این راه‌انداز به‌طور صریح Python 3.12 را انتخاب می‌کند؛ اگر پوشهٔ `.venv` قبلاً با نسخهٔ ناسازگار (مانند Python 3.15) ساخته شده باشد، فقط همان محیط مجازی را از نو می‌سازد. Python 3.12 باید نصب باشد و در `py -0p` دیده شود.

## راه‌اندازی در ویندوز

1. از این پروژه و پایگاه دادهٔ فعلی پشتیبان بگیر.
2. از `.env.example` یک کپی به نام `.env` بساز؛ توکن واقعی، `ADMIN_ID` و اطلاعات اتصال خودت را وارد کن. `.env` را برای هیچ‌کس ارسال یا در Git منتشر نکن.
3. Docker Desktop را روشن کن.
4. در PowerShell، از پوشه اصلی پروژه اجرا کن:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start.ps1
```

این اسکریپت محیط مجازی را می‌سازد، وابستگی‌ها را نصب می‌کند، PostgreSQL و Redis را بالا می‌آورد، migrationها را اجرا می‌کند و سپس ربات را اجرا می‌کند. اگر فایل `.env` وجود نداشته باشد، فقط نمونه را کپی می‌کند و برای جلوگیری از اجرای ناخواسته متوقف می‌شود تا مقادیر واقعی را تنظیم کنی.

## اجرای دستی

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env  # فقط اگر .env هنوز وجود ندارد
docker compose up -d postgres redis
python -m alembic upgrade head
python -m main
```

اگر قبلاً `.env` یا دیتابیس داری، آن‌ها را با مقادیر نمونه جایگزین نکن. مقدار `DATABASE_URL` باید با مشخصات PostgreSQL هم‌خوان باشد.

## داده‌های اولیه بازی (ویندوز مستقل)

`run_game.bat` ساختار جدول‌ها را آماده می‌کند، اما محتوای اولیهٔ مناطق، دشمنان، آیتم‌ها، تجهیزات، مهارت‌ها، مأموریت‌ها و دستورهای ساخت را به‌طور خودکار seed نمی‌کند. برای پُر کردن فهرست‌های بازی یک‌بار ربات را متوقف کن و `setup_game_content.bat` را اجرا کن. این اسکریپت به دیتابیس مستقل `eldoria.db` وصل می‌شود، داده‌های کاتالوگ را اضافه/به‌روزرسانی می‌کند و آمار نهایی را نشان می‌دهد؛ حساب شخصیت‌ها و موجودی بازیکنان را پاک نمی‌کند.

پس از موفقیت، `run_game.bat` را اجرا کن. در تلگرام `/menu` را بزن و از منوی اصلی وارد «🗺️ ماجراجویی» و سپس «مناطق ماجراجویی» شو.

برای حالت Docker/PostgreSQL، از مهاجرت‌های Alembic و روش استقرار تولیدی استفاده کن؛ اسکریپت `setup_game_content.bat` مخصوص حالت مستقل ویندوز و SQLite است.

## تست و بررسی نحوی

```powershell
python -m compileall -q .
pytest -q
```

موفقیت کامپایل به‌تنهایی به معنی سالم بودن اجرای زنده نیست. برای آزمون کامل باید PostgreSQL، Redis و ارتباط Telegram در محیط آزمایشی در دسترس باشند.

## امنیت و انتشار

- هرگز `.env`، توکن ربات، رمز پایگاه داده، پوشه `.git`، محیط مجازی یا cache را در بسته عمومی قرار نده.
- سرویس‌های دیتابیس و Redis در Compose فقط به `127.0.0.1` متصل‌اند؛ آن‌ها را بدون احراز هویت و firewall مناسب به اینترنت عمومی باز نکن.
- اگر توکن یا رمز در یک مخزن/ZIP عمومی منتشر شد، آن را فوراً تعویض کن.
- چک‌لیست `RELEASE_CHECKLIST_FA.md` باید در staging و سپس در سرور نهایی مرور شود.
- `AGENTS.md` قوانین دائمی طراحی و توسعه و دفتر ثبت ۹۵ موردی را نگه می‌دارد. موارد چک‌لیست تا زمانی که واقعاً اصلاح و تست نشده‌اند، انجام‌شده نیستند.

## ساختار کلی

- `handlers/`: ورودی‌های پیام و callback تلگرام
- `services/`: منطق بازی و عملیات دامنه
- `models/`: مدل‌های SQLAlchemy
- `keyboards/`: کیبوردهای تلگرام
- `alembic/`: مهاجرت‌های دیتابیس
- `assets/`: تصاویر و دارایی‌های بازی
- `tests/`: تست‌های خودکار موجود

## محدودیت‌های بررسی

بررسی این بسته شامل تحلیل ایستا و اجرای تست‌هایی است که محیط اجازه می‌دهد. آزمون زندهٔ Telegram/PostgreSQL/Redis باید در محیط مالک پروژه انجام شود و در گزارش انتشار جداگانه ثبت شود.


## Syncing game catalogs on Windows

Stop the bot, back up `eldoria.db`, and run `sync_catalogs.bat`. Choose `1` to sync all existing seed-backed catalogs, or choose a single catalog from the menu. See `SYNC_CATALOGS_FA.md` for details. This does not seed user-generated fan art or rebuild player-owned/progression data.
