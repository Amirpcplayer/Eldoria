from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from states.character import CharacterCreation
from services.panel_image_service import send_panel
from services.vitals_recovery_service import recover_character_vitals
from services.language_service import get_language, tr


router = Router()


MAIN_MENU_TEXT = (
    "🎮 <b>منوی اصلی اِلدوریا</b>\\n\\n"
    "🌌 ماجراجویی تو در اِلدوریا ادامه دارد..."
)

_START_TEXT = {
    "fa": {
        "welcome": "༺ 🌑 بازگشت به اِلدوریا 🌑 ༻\\n\\nقهرمان <b>{name}</b>، سرنوشتت هنوز در انتظار توست.\\n\\nبرای مشاهدهٔ وضعیت قهرمانت از /profile استفاده کن.",
        "private_start": "برای ساخت قهرمان، در گفت‌وگوی خصوصی ربات دستور /start را بزن.",
        "creation": "༺ 🌌 دروازه‌های اِلدوریا 🌌 ༻\\n\\nسکوتِ کهن شکسته است...\\nستارگان از سرنوشتی تازه خبر می‌دهند و دروازه‌های جهانی فراموش‌شده، بار دیگر گشوده می‌شوند.\\n\\n⚔️ <b>مسافر، سرنوشتت تو را فرا می‌خواند.</b>\\n\\nدر سرزمینی که قدرت با اراده سنجیده می‌شود و نام قهرمانان در افسانه‌ها جاودانه می‌ماند، نخستین قدم را تو برمی‌داری.\\n\\n📜 نامی برای قهرمانت برگزین؛ نامی که روزی در تالار افسانه‌های اِلدوریا طنین‌انداز شود.\\n\\n✍️ <b>نام قهرمانت را وارد کن:</b>\\n\\n━━━━━━━━━━━━━━━━━━\\n✦ دفتر سرنوشت اِلدوریا ✦",
    },
    "en": {
        "welcome": "༺ 🌑 Return to Eldoria 🌑 ༻\\n\\nHero <b>{name}</b>, your destiny is still waiting.\\n\\nUse /profile to view your hero.",
        "private_start": "To create a hero, send /start to the bot in a private chat.",
        "creation": "༺ 🌌 The Gates of Eldoria 🌌 ༻\\n\\nThe ancient silence has broken...\\nThe stars foretell a new destiny, and the gates to forgotten worlds open once more.\\n\\n⚔️ <b>Traveler, destiny calls for you.</b>\\n\\nIn a land where power is measured by will and heroes live on in legends, your journey begins.\\n\\n📜 Choose a name for your hero, one that may one day echo through Eldoria's Hall of Legends.\\n\\n✍️ <b>Enter your hero's name:</b>\\n\\n━━━━━━━━━━━━━━━━━━\\n✦ The Book of Destiny ✦",
    },
    "ru": {
        "welcome": "༺ 🌑 Возвращение в Элдорию 🌑 ༻\\n\\nГерой <b>{name}</b>, твоя судьба всё ещё ждёт тебя.\\n\\nИспользуй /profile, чтобы посмотреть героя.",
        "private_start": "Чтобы создать героя, отправь /start боту в личном чате.",
        "creation": "༺ 🌌 Врата Элдории 🌌 ༻\\n\\nДревняя тишина нарушена...\\nЗвёзды предвещают новую судьбу, а врата забытых миров вновь открываются.\\n\\n⚔️ <b>Путник, судьба зовёт тебя.</b>\\n\\nВ мире, где сила измеряется волей, а имена героев живут в легендах, начинается твой путь.\\n\\n📜 Выбери имя герою, которое однажды прозвучит в Зале легенд Элдории.\\n\\n✍️ <b>Введи имя своего героя:</b>\\n\\n━━━━━━━━━━━━━━━━━━\\n✦ Книга судьбы ✦",
    },
}


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    if message.from_user is None:
        return

    telegram_id = message.from_user.id
    language = await get_language(telegram_id)
    language = language if language in _START_TEXT else "fa"
    localized = _START_TEXT[language]

    async with AsyncSessionLocal() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == telegram_id)
        )

    if character:
        await recover_character_vitals(telegram_id)
        await state.clear()
        await message.answer(
            localized["welcome"].format(name=__import__("html").escape(character.name)),
            parse_mode="HTML",
        )
        return

    if message.chat.type != "private":
        bot_username = (await message.bot.get_me()).username
        if bot_username:
            await message.answer(
                localized["private_start"] + "\\n"
                f"https://t.me/{bot_username}?start=create"
            )
        else:
            await message.answer(localized["private_start"])
        return

    await state.clear()
    await state.set_state(CharacterCreation.waiting_for_name)
    await message.answer(
        localized["creation"],
        parse_mode="HTML",
        reply_to_message_id=message.message_id,
        allow_sending_without_reply=True,
    )
