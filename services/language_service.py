from __future__ import annotations

from sqlalchemy import select
from database.database import AsyncSessionLocal
from models.social_systems import PlayerSetting

LANGUAGES = {"fa", "en", "ru"}
TEXT = {
 "fa": {"main_title":"🎮 <b>منوی اصلی World Eldoria</b>","main_sub":"🌌 ماجراجویی تو در اِلدوریا ادامه دارد...","settings":"⚙️ <b>تنظیمات اِلدوریا</b>\n\nتنظیمات بازیکن خود را مدیریت کن.","rename":"✍️ تغییر نام قهرمان · ۲٬۰۰۰ Gold","language":"🌐 زبان","back":"🔙 بازگشت","choose":"🌐 <b>زبان بازی</b>\n\nزبان موردنظر خود را انتخاب کن.","saved":"✅ زبان بازی تغییر کرد.","profile":"👤 پروفایل","inventory":"🗃 صندوقچه","skills":"⚔️ مهارت‌ها","equipment":"🛡️ تجهیزات","quest":"📜 مأموریت‌ها","adventure":"🗺️ ماجراجویی","crafting":"🔨 کرفتینگ","pets":"🐾 پت","events":"🎉 ایونت","party":"👥 پارتی","guild":"🛡️ گیلد","ranking":"🏆 رتبه‌بندی","forge":"⚒️ آهنگری","marketplace":"🏪 بازار بازیکنان","bestiary":"📖 دفترچهٔ هیولا","exchange":"💱 تبدیل گلد به جم","guide":"📖 راهنما","shop":"🛒 فروشگاه"},
 "en": {"main_title":"🎮 <b>World Eldoria · Main Menu</b>","main_sub":"🌌 Your adventure in Eldoria continues...","settings":"⚙️ <b>Eldoria Settings</b>\n\nManage your player settings.","rename":"✍️ Rename hero · 2,000 Gold","language":"🌐 Language","back":"🔙 Back","choose":"🌐 <b>Game language</b>\n\nChoose your preferred language.","saved":"✅ Game language updated.","profile":"👤 Profile","inventory":"🗃 Chest","skills":"⚔️ Skills","equipment":"🛡️ Equipment","quest":"📜 Quests","adventure":"🗺️ Adventure","crafting":"🔨 Crafting","pets":"🐾 Pets","events":"🎉 Events","party":"👥 Party","guild":"🛡️ Guild","ranking":"🏆 Rankings","forge":"⚒️ Forge","marketplace":"🏪 Player Market","bestiary":"📖 Bestiary","exchange":"💱 Gold to Gems","guide":"📖 Guide","shop":"🛒 Shop"},
 "ru": {"main_title":"🎮 <b>World Eldoria · Главное меню</b>","main_sub":"🌌 Ваше приключение в Элдории продолжается...","settings":"⚙️ <b>Настройки Элдории</b>\n\nУправляйте настройками игрока.","rename":"✍️ Сменить имя · 2 000 золота","language":"🌐 Язык","back":"🔙 Назад","choose":"🌐 <b>Язык игры</b>\n\nВыберите язык.","saved":"✅ Язык игры изменён.","profile":"👤 Профиль","inventory":"🗃 Сундук","skills":"⚔️ Навыки","equipment":"🛡️ Снаряжение","quest":"📜 Задания","adventure":"🗺️ Приключения","crafting":"🔨 Ремесло","pets":"🐾 Питомцы","events":"🎉 События","party":"👥 Отряд","guild":"🛡️ Гильдия","ranking":"🏆 Рейтинг","forge":"⚒️ Кузница","marketplace":"🏪 Рынок игроков","bestiary":"📖 Бестиарий","exchange":"💱 Золото в самоцветы","guide":"📖 Помощь","shop":"🛒 Магазин"}
}

async def get_language(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        language = await session.scalar(select(PlayerSetting.language).where(PlayerSetting.telegram_id == telegram_id))
    return language if language in LANGUAGES else "fa"

def tr(language: str, key: str) -> str:
    return TEXT.get(language, TEXT["fa"]).get(key, TEXT["fa"].get(key, key))
