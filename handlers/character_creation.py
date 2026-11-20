from html import escape

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from database.database import AsyncSessionLocal
from models.character import Character
from states.character import CharacterCreation
from keyboards.character import gender_keyboard, race_keyboard
from services.language_service import get_language

router = Router()

GENDER_NAMES = {
    "male": {"fa": "مرد", "en": "Male", "ru": "Мужчина"},
    "female": {"fa": "زن", "en": "Female", "ru": "Женщина"},
}
TEXT = {
    "fa": {
        "text_only": "❌ نام قهرمان را به‌صورت متنی وارد کن.",
        "command_name": "❌ نام قهرمان نمی‌تواند شبیه دستور ربات باشد. فقط یک نام معمولی وارد کن.",
        "short": "༺ 📜 نامی برای افسانه‌ات برگزین 📜 ༻\n\nنام قهرمان باید دست‌کم ۳ حرف داشته باشد.\n\n✍️ نام دیگری وارد کن:",
        "long": "༺ 📜 نام قهرمان 📜 ༻\n\nنام قهرمان نمی‌تواند بیشتر از ۳۲ حرف باشد.\n\n✍️ نام کوتاه‌تری وارد کن:",
        "exists": "༺ ⚠️ سرنوشت از پیش نوشته شده است ⚠️ ༻\n\n👤 قهرمان ثبت‌شده: {name}\nبرای هر حساب، تنها یک قهرمان قابل ساخت است.",
        "name_taken": "༺ 🕯️ این نام پیش‌تر ثبت شده است 🕯️ ༻\n\n👤 نام انتخابی: {name}\n\nنام دیگری برگزین تا افسانه‌ات با هویتی یگانه آغاز شود.\n✍️ نام تازه را وارد کن:",
        "gender_intro": "༺ 📜 پیمان سرنوشت 📜 ༻\n\n✅ نام قهرمان در دفتر کهن ثبت شد: <b>{name}</b>\n\nاما پیش از آن‌که قدم در مسیر قدرت بگذاری، باید هویت قهرمانت را آشکار کنی.\n\n⚔️ انتخاب تو، بخشی از داستانی خواهد بود که در اِلدوریا رقم می‌زنی.\n\n⚧ <b>جنسیت قهرمانت را انتخاب کن:</b>\n\n━━━━━━━━━━━━━━━━━━\n✦ سرنوشت هنوز نوشته نشده است ✦",
        "incomplete": "اطلاعات ساخت قهرمان ناقص است؛ دوباره /start را بزن.",
        "race_intro": "༺ 🧬 میراث نیاکان 🧬 ༻\n\n✅ جنسیت قهرمان: <b>{gender}</b>\n\nدر اعماق اِلدوریا، خون نیاکان هنوز قدرتی فراموش‌نشده در خود دارد. هر نژاد، ریشه‌ای متفاوت و داستانی ویژه دارد.\n\n🌑 انتخاب تو، نخستین گام در شکل‌گیری هویت قهرمانت خواهد بود.\n\n🧬 <b>نژاد قهرمانت را انتخاب کن:</b>\n\n━━━━━━━━━━━━━━━━━━\n✦ میراثت را برگزین، قهرمان ✦",
    },
    "en": {
        "text_only": "❌ Please enter your hero's name as text.",
        "command_name": "❌ A hero name cannot look like a bot command. Enter an ordinary name.",
        "short": "༺ 📜 Choose a name for your legend 📜 ༻\n\nYour hero's name must contain at least 3 characters.\n\n✍️ Try another name:",
        "long": "༺ 📜 Hero Name 📜 ༻\n\nYour hero's name cannot exceed 32 characters.\n\n✍️ Try a shorter name:",
        "exists": "༺ ⚠️ Fate Is Already Written ⚠️ ༻\n\n👤 Registered hero: {name}\nOnly one hero can be created per account.",
        "name_taken": "༺ 🕯️ This Name Is Taken 🕯️ ༻\n\n👤 Chosen name: {name}\n\nChoose another name to begin your legend with a unique identity.\n✍️ Enter a new name:",
        "gender_intro": "༺ 📜 Pact of Fate 📜 ༻\n\n✅ Your hero's name is recorded in the ancient ledger: <b>{name}</b>\n\nBefore you begin your path to power, reveal your hero's identity.\n\n⚔️ Your choice will become part of the story you forge in Eldoria.\n\n⚧ <b>Choose your hero's gender:</b>\n\n━━━━━━━━━━━━━━━━━━\n✦ Your fate is not yet written ✦",
        "incomplete": "Character creation data is incomplete. Please use /start again.",
        "race_intro": "༺ 🧬 Ancestral Legacy 🧬 ༻\n\n✅ Hero gender: <b>{gender}</b>\n\nDeep in Eldoria, ancestral blood still holds forgotten power. Each race has its own roots and story.\n\n🌑 Your choice is the first step in shaping your hero's identity.\n\n🧬 <b>Choose your hero's race:</b>\n\n━━━━━━━━━━━━━━━━━━\n✦ Choose your legacy, hero ✦",
    },
    "ru": {
        "text_only": "❌ Введи имя героя текстом.",
        "command_name": "❌ Имя героя не должно быть похоже на команду бота. Введи обычное имя.",
        "short": "༺ 📜 Выбери имя для своей легенды 📜 ༻\n\nИмя героя должно содержать не менее 3 символов.\n\n✍️ Попробуй другое имя:",
        "long": "༺ 📜 Имя героя 📜 ༻\n\nИмя героя не может быть длиннее 32 символов.\n\n✍️ Введи имя покороче:",
        "exists": "༺ ⚠️ Судьба уже предрешена ⚠️ ༻\n\n👤 Зарегистрированный герой: {name}\nДля одного аккаунта можно создать только одного героя.",
        "name_taken": "༺ 🕯️ Это имя уже занято 🕯️ ༻\n\n👤 Выбранное имя: {name}\n\nВыбери другое имя, чтобы начать легенду с уникальной личностью.\n✍️ Введи новое имя:",
        "gender_intro": "༺ 📜 Договор судьбы 📜 ༻\n\n✅ Имя героя внесено в древний свиток: <b>{name}</b>\n\nПрежде чем встать на путь силы, раскрой личность своего героя.\n\n⚔️ Твой выбор станет частью истории, которую ты создашь в Эльдории.\n\n⚧ <b>Выбери пол героя:</b>\n\n━━━━━━━━━━━━━━━━━━\n✦ Твоя судьба ещё не написана ✦",
        "incomplete": "Данные персонажа неполные. Запусти /start ещё раз.",
        "race_intro": "༺ 🧬 Наследие предков 🧬 ༻\n\n✅ Пол героя: <b>{gender}</b>\n\nВ глубинах Эльдории кровь предков всё ещё хранит забытую силу. У каждой расы свои корни и история.\n\n🌑 Твой выбор — первый шаг к формированию личности героя.\n\n🧬 <b>Выбери расу своего героя:</b>\n\n━━━━━━━━━━━━━━━━━━\n✦ Выбери своё наследие, герой ✦",
    },
}

def _lang(language):
    return language if language in TEXT else "fa"

@router.message(CharacterCreation.waiting_for_name)
async def character_name_handler(message: Message, state: FSMContext):
    language = _lang(await get_language(message.from_user.id))
    t = TEXT[language]
    if not message.text:
        await message.answer(t["text_only"])
        return
    name = message.text.strip()
    if name.startswith(("/", "!")):
        await message.answer(t["command_name"])
        return
    if len(name) < 3:
        await message.answer(t["short"])
        return
    if len(name) > 32:
        await message.answer(t["long"])
        return

    telegram_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        existing_player = await session.scalar(select(Character).where(Character.telegram_id == telegram_id))
        if existing_player:
            await message.answer(t["exists"].format(name=escape(existing_player.name)))
            await state.clear()
            return
        existing_name = await session.scalar(select(Character).where(Character.name == name))
        if existing_name:
            await message.answer(t["name_taken"].format(name=escape(name)))
            return

    await state.update_data(name=name)
    await state.set_state(CharacterCreation.waiting_for_gender)
    await message.answer(
        t["gender_intro"].format(name=escape(name)),
        reply_markup=gender_keyboard(language),
        parse_mode=ParseMode.HTML,
    )

@router.callback_query(CharacterCreation.waiting_for_gender, lambda c: c.data and c.data.startswith("gender:"))
async def character_gender_handler(callback: CallbackQuery, state: FSMContext):
    language = _lang(await get_language(callback.from_user.id))
    t = TEXT[language]
    gender_id = callback.data.split(":", 1)[1]
    gender_name = GENDER_NAMES.get(gender_id, {}).get(language)
    data = await state.get_data()
    name = data.get("name")
    if gender_name is None or not name:
        await callback.answer(t["incomplete"], show_alert=True)
        await state.clear()
        return

    await state.update_data(gender=gender_id)
    await callback.message.answer(
        t["race_intro"].format(gender=escape(gender_name)),
        reply_markup=race_keyboard(language),
        parse_mode=ParseMode.HTML,
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()
