from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from services.panel_image_service import send_panel
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

def button(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def keyboard(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))

async def render_command_panel(message: Message, section: str) -> None:
    user_id = message.from_user.id
    panel_name = "main_menu"
    texts = {
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
        "guide": ("📖 <b>راهنمای دنیای فانتزی اِلدوریا</b>\n\nاز منوی بازی برای پروفایل، صندوقچه، مهارت‌ها، تجهیزات، ماجراجویی، مأموریت‌ها، پت‌ها، پارتی و گیلد استفاده کن.\n\n⚔️ برای مبارزه با باس گروه، روی پیام باس ریپلای کن و «حمله» یا /attack را بفرست.\n🧪 معجون سلامتی: /heal · مانا: /mana\n🏪 فروشگاه: /shop", keyboard([button("🗺️ ماجراجویی", "menu:adventure")], [button("🏪 فروشگاه", "menu:shop")], [button("🔙 منوی اصلی", "menu:back")]), "guide"),
        "exchange": ("💱 <b>صرافی اِلدوریا</b>\n\nنرخ تبدیل: ۱۰٬۰۰۰ گلد = ۱ جم. مقدار موردنظر را انتخاب کن؛ موجودی هنگام تأیید دوباره بررسی می‌شود.", keyboard([button("💱 تبدیل ۱ جم", "exchange:confirm:1")], [button("💱 تبدیل ۵ جم", "exchange:confirm:5")], [button("💱 تبدیل ۱۰ جم", "exchange:confirm:10")], [button("🔙 منوی اصلی", "menu:back")]), "exchange"),
        "settings": ("⚙️ <b>تنظیمات اِلدوریا</b>\n\nتنظیمات قابل‌دسترسی حساب خود را مدیریت کن.", keyboard([button("✍️ تغییر نام قهرمان · ۲٬۰۰۰ Gold", "settings:rename")], [button("🔙 منوی اصلی", "menu:back")]), "settings"),
    }
    text, markup, panel_name = texts[section]
    # Send the actual section panel on the command itself; no extra "open" button.
    await send_panel(message=message, panel_name=panel_name, text=text, reply_markup=markup)

@router.message(Command(*ALIASES.keys(), ignore_case=True))
async def command_alias(message: Message):
    if not message.from_user:
        return
    command = (message.text or "").split(maxsplit=1)[0].split("@", 1)[0].lstrip("/").lower()
    section = ALIASES.get(command)
    if section:
        await render_command_panel(message, section)
