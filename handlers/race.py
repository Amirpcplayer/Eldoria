from html import escape

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.character import race_keyboard
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.database import AsyncSessionLocal
from models.character import Character
from keyboards.main_menu import enter_game_keyboard
from game.stats import get_base_stats
from services.language_service import get_language

router = Router()

RACES = {
    "human": ("👤 Human", "👤 انسان", "👤 Человек",
              "Humans are adaptable and can grow along many paths.",
              "انسان‌ها انعطاف‌پذیرند و در مسیرهای گوناگون رشد می‌کنند.",
              "Люди гибки и могут развиваться разными путями."),
    "elf": ("🧝 Elf", "🧝 الف", "🧝 Эльф",
            "Elves are connected to magic and the heritage of ancient forests.",
            "الف‌ها با جادو و میراث جنگل‌های کهن پیوند دارند.",
            "Эльфы связаны с магией и наследием древних лесов."),
    "demon": ("😈 Demon", "😈 شیطان", "😈 Демон",
              "Demons wield dark power and a fierce will to fight.",
              "شیاطین از نیروی تاریک و ارادهٔ نبرد بهره می‌برند.",
              "Демоны владеют тёмной силой и несгибаемой волей к битве."),
    "dwarf": ("⛏️ Dwarf", "⛏️ دورف", "⛏️ Дворф",
              "Dwarves are known for endurance, craftsmanship, and defense.",
              "دورف‌ها به استقامت، صنعتگری و دفاع شناخته می‌شوند.",
              "Дворфы известны выносливостью, мастерством и защитой."),
    "dragonite": ("🐉 Dragonite", "🐉 درگونایت", "🐉 Драконит",
                  "Dragonites are heirs to the power of dragons.",
                  "درگونایت‌ها وارثان نیروی اژدهایان هستند.",
                  "Дракониты — наследники силы драконов."),
    "fairy": ("🧚 Fairy", "🧚 پری", "🧚 Фея",
              "Fairies rely on magical energy and agility.",
              "پری‌ها به انرژی جادویی و چابکی تکیه دارند.",
              "Феи полагаются на магическую энергию и ловкость."),
    "vampire": ("🧛 Vampire", "🧛 خون‌آشام", "🧛 Вампир",
                "Vampires draw on power and the secrets of the night.",
                "خون‌آشام‌ها از قدرت و اسرار شب بهره می‌گیرند.",
                "Вампиры черпают силу и тайны ночи."),
    "werewolf": ("🐺 Werewolf", "🐺 گرگینه", "🐺 Оборотень",
                 "Werewolves are swift and powerful warriors.",
                 "گرگینه‌ها جنگجویانی سریع و نیرومندند.",
                 "Оборотни — быстрые и могучие воины."),
}
GENDERS = {"male": ("Male", "مرد", "Мужчина"), "female": ("Female", "زن", "Женщина")}
STAT_NAMES = {
    "hp": ("Health", "سلامتی", "Здоровье"), "mana": ("Mana", "مانا", "Мана"),
    "attack": ("Attack", "حمله", "Атака"), "magic_power": ("Magic", "جادو", "Магия"),
    "defense": ("Defense", "دفاع", "Защита"), "magic_defense": ("Magic Defense", "دفاع جادویی", "Маг. защита"),
    "speed": ("Speed", "سرعت", "Скорость"), "accuracy": ("Accuracy", "دقت", "Точность"),
    "luck": ("Luck", "شانس", "Удача"), "critical": ("Critical", "بحرانی", "Крит. удар"),
}
def lang_index(language):
    return {"en": 0, "fa": 1, "ru": 2}.get(language, 1)

def boosted_stats(race_id):
    return {key: (value * 130 + 99) // 100 for key, value in get_base_stats(race_id).items()}

async def replace_panel(callback, text, markup=None):
    await callback.message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    try:
        await callback.message.delete()
    except Exception:
        pass

@router.callback_query(lambda c: c.data == "race:back")
async def race_back(callback: CallbackQuery, state: FSMContext):
    language = await get_language(callback.from_user.id)
    idx = lang_index(language)
    prompts = ("༺ 🧬 Ancestral Legacy 🧬 ༻\n\nChoose your hero's race:",
               "༺ 🧬 میراث نیاکان 🧬 ༻\n\nنژاد قهرمانت را انتخاب کن:",
               "༺ 🧬 Наследие предков 🧬 ༻\n\nВыбери расу своего героя:")
    await state.update_data(selected_race=None)
    await replace_panel(callback, prompts[idx], race_keyboard(language))
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("race:") and c.data not in ("race:back", "race:confirm"))
async def race_preview(callback: CallbackQuery, state: FSMContext):
    language = await get_language(callback.from_user.id)
    idx = lang_index(language)
    race_id = callback.data.split(":", 1)[1]
    data = await state.get_data()
    if race_id not in RACES or not data.get("name") or data.get("gender") not in GENDERS:
        await callback.answer(("Complete character creation with /start first.", "ابتدا /start را بزن و مراحل ساخت شخصیت را کامل کن.", "Сначала запусти /start и заверши создание персонажа.")[idx], show_alert=True)
        return
    await state.update_data(selected_race=race_id)
    stats = boosted_stats(race_id)
    lines = "\n".join(f"✦ <b>{STAT_NAMES[key][idx]}:</b> {stats[key]:,}" for key in STAT_NAMES if key in stats)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=("✅ Confirm race", "✅ تأیید نژاد", "✅ Подтвердить расу")[idx], callback_data="race:confirm")],
        [InlineKeyboardButton(text=("↩️ Back to races", "↩️ بازگشت به نژادها", "↩️ К выбору рас")[idx], callback_data="race:back")],
    ])
    titles = ("Starting stats (+30%)", "قدرت آغازین (+۳۰٪)", "Начальные характеристики (+30%)")
    gifts = ("🪙 Starting gift: 500 Gold", "🪙 هدیهٔ شروع: ۵۰۰ گلد", "🪙 Стартовый подарок: 500 золота")
    asks = ("Confirm this race?", "آیا این نژاد را تأیید می‌کنی؟", "Подтвердить эту расу?")
    await replace_panel(callback, f"༺ 🧬 {RACES[race_id][idx]} 🧬 ༻\n\n{RACES[race_id][idx+3]}\n\n<b>📊 {titles[idx]}</b>\n{lines}\n\n{gifts[idx]}\n\n{asks[idx]}", kb)
    await callback.answer()

@router.callback_query(lambda c: c.data == "race:confirm")
async def race_handler(callback: CallbackQuery, state: FSMContext):
    language = await get_language(callback.from_user.id)
    idx = lang_index(language)
    data = await state.get_data()
    race_id = data.get("selected_race")
    if race_id not in RACES:
        await callback.answer(("Choose a race first.", "ابتدا یک نژاد انتخاب کن.", "Сначала выбери расу.")[idx], show_alert=True)
        return
    name = data.get("name")
    gender_id = data.get("gender")
    if not isinstance(name, str) or not name.strip() or name.strip().startswith(("/", "!")) or len(name.strip()) < 3 or len(name.strip()) > 32:
        await callback.answer(("Invalid hero name; restart with /start.", "نام قهرمان معتبر نیست؛ دوباره از /start نام تازه‌ای انتخاب کن.", "Недопустимое имя героя; начни заново через /start.")[idx], show_alert=True)
        await state.clear()
        return
    name = name.strip()
    if gender_id not in GENDERS:
        await callback.answer(("Character details are incomplete; use /start.", "اطلاعات ناقص است؛ /start را بزن.", "Данные персонажа неполные; используй /start.")[idx], show_alert=True)
        await state.clear()
        return
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(Character).where(Character.telegram_id == callback.from_user.id))
        if existing:
            await callback.answer(("Your character already exists.", "شخصیت شما قبلاً ساخته شده است.", "Твой персонаж уже создан.")[idx], show_alert=True)
            await state.clear()
            return
        stats = boosted_stats(race_id)
        character = Character(telegram_id=callback.from_user.id, telegram_username=callback.from_user.username,
            name=name, race=race_id, gender=gender_id, gold=500,
            hp=stats["hp"], max_hp=stats["hp"], mana=stats["mana"], max_mana=stats["mana"],
            **{k:stats[k] for k in ("attack", "magic_power", "defense", "magic_defense", "speed", "accuracy", "luck", "critical")})
        session.add(character)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await callback.answer(("This account or name is already registered.", "این حساب یا نام قبلاً ثبت شده است.", "Этот аккаунт или имя уже зарегистрированы.")[idx], show_alert=True)
            await state.clear()
            return
    await state.clear()
    text = (
        f"༺ ✨ Hero Awakening ✨ ༻\n\nDestiny's light shines upon {escape(name)}...\n\n⚔️ Race: {RACES[race_id][idx]}\n🪙 Starting Gold: 500\n📈 Base stats: +30%\n\n✦ Your legend begins ✦",
        f"༺ ✨ بیداری قهرمان ✨ ༻\n\nنور سرنوشت بر {escape(name)} تابید...\n\n⚔️ نژاد: {RACES[race_id][idx]}\n🪙 طلای آغازین: ۵۰۰\n📈 قدرت پایه: ۳۰٪ بیشتر\n\n✦ افسانهٔ تو آغاز شد ✦",
        f"༺ ✨ Пробуждение героя ✨ ༻\n\nСвет судьбы озарил {escape(name)}...\n\n⚔️ Раса: {RACES[race_id][idx]}\n🪙 Стартовое золото: 500\n📈 Базовые характеристики: +30%\n\n✦ Твоя легенда начинается ✦",
    )
    await replace_panel(callback, text[idx], enter_game_keyboard(language))
    await callback.answer()
