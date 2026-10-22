# مرحلهٔ ۱۴ — برنامهٔ اجرای تست فشار

## وضعیت
آماده‌سازی اجرای تست فشار انجام شد؛ تست بار واقعی هنوز اجرا نشده، چون این مخزن به محیط staging فعال یا رمزهای اتصال آن دسترسی ندارد. ربات اصلی عمداً اجرا نشده است.

## ترتیب اجرای امن روی سیستم staging
از PowerShell در ریشهٔ پروژه استفاده کنید. ابتدا Docker Compose را بازبینی و فقط سرویس‌های جداگانه را بالا بیاورید:

```powershell
$env:STAGING_POSTGRES_PASSWORD = "<strong-random-password>"
$env:STAGING_REDIS_PASSWORD = "<different-strong-random-password>"
docker compose -f docker-compose.staging.yml config --quiet
if ($LASTEXITCODE -ne 0) { throw "Compose validation failed" }
docker compose -f docker-compose.staging.yml up -d
docker compose -f docker-compose.staging.yml ps
```

قبل از benchmark، وضعیت هر دو سرویس باید healthy باشد. اگر پورت‌های staging از قبل اشغال‌اند یا سرویس‌ها unhealthy هستند، متوقف شوید و مشکل را بررسی کنید؛ پورت یا volume محیط اصلی را تغییر ندهید.

## Redis microbenchmark
این ابزار فقط Redis SET/GET را می‌سنجد و به‌تنهایی ظرفیت bot را مشخص نمی‌کند. پس از تأیید مقصد Redis staging، URL را به متغیر محیطی بدهید؛ برای ساده‌ترشدن parsing از رمز تصادفی متشکل از حروف و اعداد استفاده کنید و URL را چاپ نکنید.

```powershell
$env:ELDORIA_BENCHMARK_REDIS_URL = "redis://:<URL_ENCODED_PASSWORD>@127.0.0.1:16379/0"
python scripts/benchmark_redis_concurrency.py --confirm-isolated-redis --operations 2000 --levels 1,10,50,100,500
```

اگر هر سطح موفق بود و منابع staging پایدار ماندند، می‌توان بعداً تعداد عملیات را مرحله‌ای افزایش داد. اگر خطا، timeout یا افت شدید latency رخ داد، تست را متوقف و نتیجه را ذخیره کنید. رمز اتصال را در خروجی، گزارش یا Git قرار ندهید.

## چه چیزهایی باید ثبت شوند
- commit دقیق شاخهٔ آزمایش
- نسخه و منابع CPU/RAM ماشین staging
- وضعیت healthcheck قبل و بعد از تست
- pairs/s و p50/p95/p99 هر سطح concurrency
- خطاها، timeoutها، مصرف CPU/RAM و حافظهٔ Redis
- تعداد اتصال‌های PostgreSQL/Redis در صورت اجرای تست یکپارچه

## محدودیت مهم
این benchmark شبیه‌سازی ۵۰۰ کاربر Telegram نیست؛ هر worker فقط یک جریان SET سپس GET را اجرا می‌کند. ظرفیت نهایی باید با تست یکپارچهٔ handlerها، دیتابیس، قفل‌ها و زمان‌بندها در محیط staging و دادهٔ آزمایشی سنجیده شود. هیچ معیار قبولی عددی تا پیش از ثبت baseline و تعیین SLOهای پروژه فرض نشده است.

## پایان امن
```powershell
docker compose -f docker-compose.staging.yml down
```

این دستور containerها را متوقف می‌کند ولی volumeها را نگه می‌دارد. از `down -v` استفاده نکنید مگر اینکه عمداً بخواهید داده‌های آزمایشی را پاک کنید.
