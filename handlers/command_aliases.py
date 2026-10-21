from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from services.panel_image_service import send_panel, show_panel
from keyboards.inventory import inventory_keyboard
from keyboards.skills import skills_main_keyboard
from keyboards.equipment import equipment_main_keyboard
from keyboards.quest import quest_main_keyboard
from keyboards.adventure import adventure_main_keyboard
from keyboards.shop import shop_main_keyboard
from database.database import AsyncSessionLocal
from sqlalchemy import select
from models.character import Character

router = Router(name="command_aliases")

ALIASES = {
    "sandoghche": "inventory",
    "skills": "skills",
    "tajhizat": "equipment",
    "mamoriah": "quest",
    "mamoriat": "quest",
    "majarajoyi": "adventure",
    "majarajooei": "adventure",
    "crafting": "crafting",
    "pet": "pets",
    "event": "events",
    "parti": "party",
    "party": "party",
    "guild": "guild",
    "player_shop": "marketplace",
    "ahangari": "forge",
    "help": "guide",
    "change": "exchange",
    "setting": "settings",
    "settings": "settings",
}


TEXT_ALIASES = {
    "صندوقچه": "inventory",
    "مهارت ها": "skills",
    "مهارت‌ها": "skills",
    "تجهیزات": "equipment",
    "ماموریت ها": "quest",
    "ماموریت‌ها": "quest",
    "ماموریت": "quest",
    "ماجراجویی": "adventure",
    "کرفتینگ": "crafting",
    "ساخت": "crafting",
    "پت": "pets",
    "حیوانات": "pets",
    "ایونت": "events",
    "رویداد": "events",
    "پارتی": "party",
    "گیلد": "guild",
    "گیلـد": "guild",
    "بازار بازیکنان": "marketplace",
    "بازار": "marketplace",
    "آهنگری": "forge",
    "راهنما": "guide",
    "تبدیل": "exchange",
    "صرافی": "exchange",
    "تنظیمات": "settings",
    "فروشگاه": "shop",
    "منو": "main_menu",
}

def button(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def keyboard(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))

async def render_command_panel(message: Message, section: str) -> None:
    user_id = message.from_user.id
    panel_name = "main_menu"
    texts = {
        "main_menu": ("🎮 <b>منوی اصلی اِلدوریا</b>\n\n🌌 ماجراجویی تو در اِلدوریا ادامه دارد...", keyboard([button("🗺️ ماجراجویی", "menu:adventure")], [button("🏪 فروشگاه", "menu:shop")], [button("🔙 منوی اصلی", "menu:back")]), "main_menu"),
        "inventory": ("🗃 <b>صندوقچهٔ قهرمان</b>\n\nآیتم‌ها، مواد اولیه، اسکرول‌ها و فن‌آرت‌هایت را مدیریت کن.", inventory_keyboard(), "inventory"),
        "skills": ("⚔️ <b>مهارت‌های قهرمان</b>\n\nمهارت‌هایت را یاد بگیر، مشاهده و ارتقا بده.", skills_main_keyboard(), "skills"),
        "equipment": ("🛡️ <b>تجهیزات قهرمان</b>\n\nتجهیزاتت را مشاهده و مدیریت کن.", equipment_main_keyboard(), "equipment"),
        "quest": ("📜 <b>مأموریت‌های اِلدوریا</b>\n\nمأموریت‌های داستانی، روزانه و دستاوردها را بررسی کن.", quest_main_keyboard(), "quest"),
        "adventure": ("🗺️ <b>ماجراجویی اِلدوریا</b>\n\nمنطقه‌ای را انتخاب کن و برای نبرد و کسب پاداش آماده شو.", adventure_main_keyboard(), "adventure"),
        "shop": ("🏪 <b>فروشگاه اِلدوریا</b>\n\nدسته‌بندی موردنظر را انتخاب کن.", shop_main_keyboard(), "shop"),
        "crafting": ("🔨 <b>کارگاه کرفتینگ اِلدوریا</b>\n\nدستور ساخت را انتخاب کن و مواد اولیه‌ات را به تجهیزات و آیتم تبدیل کن.", keyboard([button("📜 مشاهدهٔ دستورهای ساخت", "menu:crafting")], [button("🔙 منوی اصلی", "menu:back")]), "crafting"),
        "pets": ("🐾 <b>همراهان اِلدوریا</b>\n\nپت‌هایت را مدیریت کن، پت تازه بگیر یا پت فعال را تمرین بده.", keyboard([button("🐾 حیوانات من", "pets:list")], [button("🛒 بازار پت‌ها", "pets:market")], [button("✨ تمرین / تکامل پت فعال", "pets:evolve")], [button("🔙 منوی اصلی", "menu:back")]), "pets"),
        "events": ("🎉 <b>رویدادهای اِلدوریا</b>\n\nوضعیت رویدادهای ویژه را بررسی کن.", keyboard([button("🎉 رویدادهای فعال", "events:list")], [button("🔙 منوی اصلی", "menu:back")]), "events"),
        "party": ("👥 <b>پارتی اِلدوریا</b>\n\nپارتی بساز، به پارتی بپیوند یا اعضا را مدیریت کن.", keyboard([button("➕ ساخت پارتی", "party:create")], [button("🔗 پیوستن به پارتی", "party:join")], [button("👥 اطلاعات و اعضای پارتی", "party:members")], [button("🔙 منوی اصلی", "menu:back")]), "party"),
        "guild": ("🛡️ <b>تالار گیلدهای اِلدوریا</b>\n\nگیلد بساز، به گیلد بپیوند یا گیلدها را بررسی کن.", keyboard([button("🏰 ساخت گیلد", "guild:create")], [button("🔎 یافتن گیلدها", "guild:rankings")], [button("🔗 پیوستن با شناسه", "guild:join")], [button("🔙 منوی اصلی", "menu:back")]), "guild"),
        "marketplace": ("🏪 <b>بازار بازیکنان اِلدوریا</b>\n\nآگهی‌ها را بررسی کن یا آیتم‌هایت را برای فروش ثبت کن.", keyboard([button("🛒 آگهی‌های بازار", "market:browse")], [button("📦 آگهی‌های من", "market:mine")], [button("➕ ثبت آگهی از صندوقچه", "market:sell:home")], [button("❔ راهنمای بازار", "market:help")], [button("🔙 منوی اصلی", "menu:back")]), "marketplace"),
        "forge": ("⚒️ <b>آهنگری اِلدوریا</b>\n\nتجهیزاتت را انتخاب و با گلد و مواد اولیه ارتقا بده.", keyboard([button("⚒️ باز کردن آهنگری", "menu:forge")], [button("🛡️ تجهیزات", "menu:equipment")], [button("🔙 منوی اصلی", "menu:back")]), "forge"),
        "guide": ("📖 <b>کتاب راهنمای اِلدوریا</b>\n\nقهرمان، این دفترچه دو مسیر پیش روی تو می‌گذارد. اگر تازه وارد جهان اِلدوریا شده‌ای، از پیشرفت سریع آغاز کن؛ اگر می‌خواهی با سامانه‌های بازی آشنا شوی، راهنمای جامع را بخوان.\n\n✦ هر زمان خواستی می‌توانی به این صفحه بازگردی.", keyboard([button("⚡ راهنمای پیشرفت سریع", "guide:quick")], [button("📚 راهنمای جامع", "guide:full")], [button("🔙 منوی اصلی", "menu:back")]), "guide"),
        "exchange": ("💱 <b>صرافی اِلدوریا</b>\n\nنرخ تبدیل: ۱۰٬۰۰۰ گلد = ۱ جم. مقدار موردنظر را انتخاب کن؛ موجودی هنگام تأیید دوباره بررسی می‌شود.", keyboard([button("💱 تبدیل ۱ جم", "exchange:confirm:1")], [button("💱 تبدیل ۵ جم", "exchange:confirm:5")], [button("💱 تبدیل ۱۰ جم", "exchange:confirm:10")], [button("🔙 منوی اصلی", "menu:back")]), "exchange"),
        "settings": ("⚙️ <b>تنظیمات اِلدوریا</b>\n\nتنظیمات قابل‌دسترسی حساب خود را مدیریت کن.", keyboard([button("✍️ تغییر نام قهرمان · ۲٬۰۰۰ Gold", "settings:rename")], [button("🔙 منوی اصلی", "menu:back")]), "settings"),
    }
    text, markup, panel_name = texts[section]
    # Send the actual section panel on the command itself; no extra "open" button.
    await send_panel(message=message, panel_name=panel_name, text=text, reply_markup=markup)


QUICK_GUIDE_TEXT = (
    "⚡ <b>راهنمای پیشرفت سریع قهرمان</b>\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "🌱 <b>۱. قهرمانت را بشناس</b>\n"
    "پروفایل را باز کن تا سطح، نژاد و وضعیت قهرمانت را ببینی. صندوقچه محل نگهداری آیتم‌ها و منابع توست.\n\n"
    "🗺️ <b>۲. ماجراجویی را جدی بگیر</b>\n"
    "منطقه‌ای متناسب با سطح خودت انتخاب کن. پیروزی‌ها راهی برای گرفتن تجربه، گلد و منابع هستند؛ پیش از ورود، وضعیت سلامتی و مانایت را بررسی کن.\n\n"
    "⚔️ <b>۳. قدرتت را درست بساز</b>\n"
    "مهارت‌ها را یاد بگیر و مهارت‌های فعال را در محدودهٔ اسلات‌های قهرمان تنظیم کن. تجهیزات مناسب بپوش و در آهنگری، وقتی مواد و گلد کافی داری، تجهیزات را ارتقا بده.\n\n"
    "🧪 <b>۴. منابع را هدر نده</b>\n"
    "آیتم‌ها و مواد را در صندوقچه بررسی کن. معجون سلامتی و مانا را هنگام نیاز مصرف کن؛ مواد کرفتینگ را برای دستور ساخت‌های موردنیازت نگه دار.\n\n"
    "📜 <b>۵. مأموریت‌ها را پیگیری کن</b>\n"
    "بخش مأموریت‌ها را مرتب ببین و پاداش‌های قابل دریافت را از دست نده. برای پیشرفت گروهی می‌توانی پارتی یا گیلد تشکیل بدهی یا به یکی بپیوندی.\n\n"
    "💰 <b>۶. گلد را هوشمندانه خرج کن</b>\n"
    "قبل از خرید، ببین آیا همان گلد برای ارتقای تجهیز، کرفتینگ یا نیاز فوری‌ات مفیدتر است. بازار بازیکنان را هم برای بررسی آگهی‌ها بشناس.\n\n"
    "🐾 <b>۷. همراهانت را فراموش نکن</b>\n"
    "بخش پت را برای دیدن همراهان، بازار و تمرین پت فعال بررسی کن.\n\n"
    "✦ <i>قانون طلایی: اول بقا، بعد قدرت؛ اول نیاز واقعی، بعد خریدهای تجملی.</i>"
)

FULL_GUIDE_TEXT = (
    "📚 <b>راهنمای جامع دنیای فانتزی اِلدوریا</b>\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "🌌 <b>آغاز سفر</b>\n"
    "از منوی اصلی وارد بخش‌های مختلف شو. پروفایل نمای کلی قهرمان را نشان می‌دهد و صندوقچه برای بررسی آیتم‌ها، مواد اولیه، معجون‌ها و اقلام قابل استفاده است.\n\n"
    "👤 <b>پروفایل و پیشرفت</b>\n"
    "سطح و تجربه مسیر رشد قهرمان را نشان می‌دهند. وضعیت قهرمان را مرتب بررسی کن و برای انتخاب مسیر بعدی، سطح و توان فعلی‌ات را در نظر بگیر.\n\n"
    "🗺️ <b>ماجراجویی و نبرد</b>\n"
    "در ماجراجویی منطقه را انتخاب کن و با دشمنان روبه‌رو شو. نبردهای ماجراجویی با حمله به باس‌های گروهی و مبارزهٔ PvP یکی نیستند؛ هرکدام از بخش مربوط به خودشان پیگیری می‌شوند.\n\n"
    "🐉 <b>باس گروه</b>\n"
    "برای حمله به باس فعال گروه، روی پیام همان باس ریپلای کن و «حمله» یا /attack را بفرست. دستورهای /heal و /mana برای مصرف معجون سلامتی و مانا هستند. اگر ربات از گروه حذف شده باشد، مدیر گروه باید دوباره آن را اضافه کند.\n\n"
    "⚔️ <b>مهارت‌ها و عناصر</b>\n"
    "از بخش مهارت‌ها، مهارت‌ها را یاد بگیر، سطحشان را بالا ببر و مهارت‌های فعال را متناسب با اسلات‌های قابل استفاده تنظیم کن. عناصر جادویی مختلف سبک‌های مبارزهٔ متفاوتی دارند.\n\n"
    "🛡️ <b>تجهیزات و آهنگری</b>\n"
    "در تجهیزات، وسایل قهرمان را مدیریت کن. آهنگری برای ارتقای تجهیزات با گلد و مواد لازم است؛ قبل از ارتقا، هزینه و منابع موردنیاز را بررسی کن.\n\n"
    "🎒 <b>صندوقچه، مواد و کرفتینگ</b>\n"
    "صندوقچه موجودی تو را نگه می‌دارد. مواد اولیه‌ای که در ماجراجویی به دست می‌آوری می‌توانند برای دستورهای کرفتینگ مصرف شوند. هنگام ساخت، دستور، تعداد، سطح لازم، هزینه و مواد موردنیاز را بررسی کن.\n\n"
    "🧪 <b>معجون‌ها و اسکرول‌ها</b>\n"
    "توضیحات آیتم را پیش از مصرف بخوان و آیتم را برای زمان مناسب نگه دار. فقط آیتم‌هایی که گزینهٔ استفاده دارند از همان مسیر قابل استفاده‌اند.\n\n"
    "📜 <b>مأموریت‌ها و پاداش‌ها</b>\n"
    "بخش مأموریت‌ها را برای مأموریت‌های در دسترس و پاداش‌ها بررسی کن. برخی فعالیت‌ها ممکن است شرط سطح، انجام کار یا دریافت جداگانهٔ جایزه داشته باشند.\n\n"
    "🐾 <b>پت‌ها</b>\n"
    "در بخش پت، همراهانت را مشاهده کن، از بازار پت‌ها استفاده کن و پت فعال را در صورت پشتیبانی گزینه‌ها تمرین بده. پت فعال می‌تواند در قدرت قهرمان اثر بگذارد.\n\n"
    "👥 <b>پارتی و گیلد</b>\n"
    "پارتی برای همراه‌شدن با بازیکنان دیگر و فعالیت‌های گروهی است. گیلد امکان عضویت و مدیریت گروه بلندمدت را فراهم می‌کند؛ هزینه‌ها و شرایط هر عملیات را قبل از تأیید بخوان.\n\n"
    "🏪 <b>فروشگاه، صرافی و بازار بازیکنان</b>\n"
    "فروشگاه برای خریدهای درون‌بازی است. صرافی تبدیل گلد به جم را با نرخ و مقدار تأییدشده انجام می‌دهد. بازار بازیکنان برای دیدن آگهی‌ها و معاملهٔ اقلام پشتیبانی‌شده است؛ شرایط آگهی را با دقت بررسی کن.\n\n"
    "🎨 <b>فن‌آرت</b>\n"
    "از بخش فن‌آرت، آثار ویژه را ببین. موجودی، قیمت و وضعیت هر اثر ممکن است محدود باشد؛ جزئیات همان پنل را ملاک قرار بده.\n\n"
    "⚙️ <b>تنظیمات و کمک</b>\n"
    "در تنظیمات، گزینه‌های موجود برای حسابت را مدیریت کن. تغییر نام قهرمان از همان بخش انجام می‌شود و ممکن است هزینه داشته باشد. برای دسترسی به پنل‌ها می‌توانی از دکمه‌های منو یا فرمان‌های ثبت‌شدهٔ ربات استفاده کنی.\n\n"
    "✦ <i>یادآوری: دکمه‌ها و توضیحات هر پنل، شرایط فعلی همان قابلیت را مشخص می‌کنند.</i>"
)

def guide_keyboard() -> InlineKeyboardMarkup:
    return keyboard(
        [button("⚡ راهنمای پیشرفت سریع", "guide:quick")],
        [button("📚 راهنمای جامع", "guide:full")],
        [button("🔙 منوی اصلی", "menu:back")],
    )

@router.callback_query(F.data == "menu:guide")
async def guide_menu_callback(callback: CallbackQuery) -> None:
    await show_panel(
        callback=callback,
        panel_name="guide",
        text="📖 <b>کتاب راهنمای اِلدوریا</b>\n\nیکی از دو مسیر زیر را انتخاب کن تا سفر خود را آسان‌تر آغاز کنی.",
        reply_markup=guide_keyboard(),
    )
    await callback.answer()

@router.callback_query(F.data == "guide:quick")
async def quick_guide_callback(callback: CallbackQuery) -> None:
    await show_panel(
        callback=callback,
        panel_name="guide",
        text=QUICK_GUIDE_TEXT,
        reply_markup=keyboard(
            [button("📚 راهنمای جامع", "guide:full")],
            [button("↩️ بازگشت به راهنما", "guide:back")],
            [button("🔙 منوی اصلی", "menu:back")],
        ),
    )
    await callback.answer()

@router.callback_query(F.data == "guide:full")
async def full_guide_callback(callback: CallbackQuery) -> None:
    await show_panel(
        callback=callback,
        panel_name="guide",
        text=FULL_GUIDE_TEXT,
        reply_markup=keyboard(
            [button("⚡ راهنمای پیشرفت سریع", "guide:quick")],
            [button("↩️ بازگشت به راهنما", "guide:back")],
            [button("🔙 منوی اصلی", "menu:back")],
        ),
    )
    await callback.answer()

@router.callback_query(F.data == "guide:back")
async def guide_back_callback(callback: CallbackQuery) -> None:
    await show_panel(
        callback=callback,
        panel_name="guide",
        text="📖 <b>کتاب راهنمای اِلدوریا</b>\n\nیکی از دو مسیر زیر را انتخاب کن تا سفر خود را آسان‌تر آغاز کنی.",
        reply_markup=guide_keyboard(),
    )
    await callback.answer()


@router.message(Command(*ALIASES.keys(), ignore_case=True))
async def command_alias(message: Message):
    if not message.from_user:
        return
    command = (message.text or "").split(maxsplit=1)[0].split("@", 1)[0].lstrip("/").lower()
    section = ALIASES.get(command)
    if section:
        await render_command_panel(message, section)

@router.message(F.text.func(lambda text: bool(text) and text.strip().casefold() in TEXT_ALIASES))
async def text_alias(message: Message):
    if not message.from_user:
        return
    phrase = (message.text or "").strip().casefold()
    section = TEXT_ALIASES.get(phrase)
    if section:
        if section == "main_menu":
            from handlers.main_menu import MAIN_MENU_TEXT
            from keyboards.main_menu import main_menu_keyboard
            await send_panel(message=message, panel_name="main_menu", text=MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
        else:
            await render_command_panel(message, section)
