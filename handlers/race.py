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


router = Router()

RACE_NAMES = {
    "human": "👤 انسان",
    "elf": "🧝 الف",
    "demon": "😈 شیطان",
    "dwarf": "⛏️ دورف",
    "dragonite": "🐉 درگونایت",
    "fairy": "🧚 پری",
    "vampire": "🧛 خون‌آشام",
    "werewolf": "🐺 گرگینه",
}
GENDER_NAMES = {"male": "مرد", "female": "زن"}


RACE_LORE = {
    "human": "انسان‌ها انعطاف‌پذیرند و در مسیرهای گوناگون رشد می‌کنند.",
    "elf": "الف‌ها با جادو و میراث جنگل‌های کهن پیوند دارند.",
    "demon": "شیاطین از نیروی تاریک و ارادهٔ نبرد بهره می‌برند.",
    "dwarf": "دورف‌ها به استقامت، صنعتگری و دفاع شناخته می‌شوند.",
    "dragonite": "درگونایت‌ها وارثان نیروی اژدهایان هستند.",
    "fairy": "پری‌ها به انرژی جادویی و چابکی تکیه دارند.",
    "vampire": "خون‌آشام‌ها از قدرت و اسرار شب بهره می‌گیرند.",
    "werewolf": "گرگینه‌ها جنگجویانی سریع و نیرومندند.",
}
STAT_NAMES = {"hp":"سلامتی", "mana":"مانا", "attack":"حمله", "magic_power":"جادو", "defense":"دفاع", "magic_defense":"دفاع جادویی", "speed":"سرعت", "accuracy":"دقت", "luck":"شانس", "critical":"بحرانی"}
def boosted_stats(race_id):
    return {key: (value * 130 + 99) // 100 for key, value in get_base_stats(race_id).items()}

async def replace_panel(callback, text, markup=None):
    """Edit the current character-creation panel instead of stacking messages."""
    await replace_panel_with_text(
        callback=callback,
        text=text,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
    )

@router.callback_query(lambda c: c.data == "race:back")
async def race_back(callback: CallbackQuery, state: FSMContext):
    await state.update_data(selected_race=None)
    await replace_panel(callback, "༺ 🧬 میراث نیاکان 🧬 ༻\n\nنژاد قهرمانت را انتخاب کن:", race_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("race:") and c.data not in ("race:back", "race:confirm"))
async def race_preview(callback: CallbackQuery, state: FSMContext):
    race_id = callback.data.split(":", 1)[1]
    data = await state.get_data()
    if race_id not in RACE_NAMES or not data.get("name") or data.get("gender") not in GENDER_NAMES:
        await callback.answer("ابتدا /start را بزن و مراحل ساخت شخصیت را کامل کن.", show_alert=True)
        return
    await state.update_data(selected_race=race_id)
    stats = boosted_stats(race_id)
    lines = "\n".join(f"✦ <b>{title}:</b> {stats[key]:,}" for key, title in STAT_NAMES.items() if key in stats)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأیید نژاد", callback_data="race:confirm")],
        [InlineKeyboardButton(text="↩️ بازگشت به نژادها", callback_data="race:back")],
    ])
    await replace_panel(callback, f"༺ 🧬 {RACE_NAMES[race_id]} 🧬 ༻\n\n{RACE_LORE[race_id]}\n\n<b>📊 قدرت آغازین (+۳۰٪)</b>\n{lines}\n\n🪙 هدیهٔ شروع: ۵۰۰ گلد\n\nآیا این نژاد را تأیید می‌کنی؟", kb)
    await callback.answer()

@router.callback_query(lambda c: c.data == "race:confirm")
async def race_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    race_id = data.get("selected_race")
    race_name = RACE_NAMES.get(race_id)
    if race_name is None:
        await callback.answer("ابتدا یک نژاد انتخاب کن.", show_alert=True)
        return
    name = data.get("name")
    gender_id = data.get("gender")
    gender_name = GENDER_NAMES.get(gender_id)
    if not name or not gender_name:
        await callback.answer("اطلاعات ناقص است؛ /start را بزن.", show_alert=True)
        await state.clear()
        return
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(Character).where(Character.telegram_id == callback.from_user.id))
        if existing:
            await callback.answer("شخصیت شما قبلاً ساخته شده است.", show_alert=True)
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
            await callback.answer("این حساب یا نام قبلاً ثبت شده است.", show_alert=True)
            await state.clear()
            return
    await state.clear()
    await replace_panel(callback, f"༺ ✨ بیداری قهرمان ✨ ༻\n\nنور سرنوشت بر {escape(name)} تابید...\n\n⚔️ نژاد: {race_name}\n🪙 طلای آغازین: ۵۰۰\n📈 قدرت پایه: ۳۰٪ بیشتر\n\n✦ افسانهٔ تو آغاز شد ✦", enter_game_keyboard())
    await callback.answer()
