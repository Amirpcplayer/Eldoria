# مرحلهٔ ۱۲ — آماده‌سازی محیط آزمایشی جداگانه

## هدف
فراهم‌کردن PostgreSQL و Redis مجزا برای تست‌های کنترل‌شده، بدون اجرای ربات و بدون لمس volume یا پورت‌های محیط اصلی.

## ایزوله‌سازی
- PostgreSQL staging از پورت محلی `15432` و volume با نام مستقل استفاده می‌کند.
- Redis staging از پورت محلی `16379` و volume با نام مستقل استفاده می‌کند؛ دسترسی Redis با رمز عبور محافظت می‌شود.
- Compose هیچ سرویس bot ندارد. این فایل عمداً ربات را اجرا نمی‌کند.
- هیچ benchmark یا migration واقعی در این مرحله اجرا نشده است.

## بررسی در PowerShell
از ریشهٔ پروژه، در پنجرهٔ PowerShell مخصوص staging، رمزهای قوی و تصادفی را تعیین کنید. آن‌ها را در Git، فایل‌های commitشده یا اسکرین‌شات‌ها قرار ندهید:

```powershell
$env:STAGING_POSTGRES_PASSWORD = "<strong-random-password>"
$env:STAGING_REDIS_PASSWORD = "<different-strong-random-password>"
docker compose -f docker-compose.staging.yml config
docker compose -f docker-compose.staging.yml up -d
docker compose -f docker-compose.staging.yml ps
```

قبل از اجرا، خروجی `docker compose ... config` را بازبینی کنید و مطمئن شوید فقط سرویس‌های `postgres-staging` و `redis-staging` دیده می‌شوند. اگر Docker در دسترس نیست، این مرحله را فقط به‌عنوان فایل آمادهٔ بررسی در نظر بگیرید؛ نتیجهٔ اجرا را ادعا نکنید.

## اتصال benchmark به Redis آزمایشی
با همان رمز Redis staging، متغیر اتصال را تنظیم کنید. رمز را داخل تاریخچهٔ Git یا گزارش‌ها ننویسید:

```powershell
$env:ELDORIA_BENCHMARK_REDIS_URL = "redis://:<STAGING_REDIS_PASSWORD>@127.0.0.1:16379/0"
```

برای جلوگیری از نمایش رمز در تاریخچهٔ فرمان، بهتر است URL را با یک روش محلی و امن وارد کنید؛ پس از ساخت URL نیز آن را چاپ نکنید. فقط بعد از تأیید اینکه مقصد staging و قابل‌دورریختن است، benchmark را اجرا کنید.

## توقف محیط آزمایشی
```powershell
docker compose -f docker-compose.staging.yml down
```

این دستور volumeها را حذف نمی‌کند. حذف volumeها داده‌های staging را از بین می‌برد و باید فقط در صورت قصد صریح انجام شود.

## مرحلهٔ بعد
روی همین سرویس‌های جداگانه ابتدا اتصال و healthcheck را تأیید کنید، سپس benchmark Redis را اجرا و خروجی خام را ثبت کنید. بعد از آن تست‌های یکپارچهٔ PostgreSQL/Redis را اضافه کنید. هرگز URL یا volume محیط تولید را برای این آزمایش استفاده نکنید.
