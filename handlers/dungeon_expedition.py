from __future__ import annotations

import html
import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from middlewares.panel_owner import protect_keyboard
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from bot.bot import bot
from config.settings import settings
from database.database import AsyncSessionLocal
from models.social_systems import DungeonLoot, GroupDungeonEvent
from models.world_systems import GroupBoss
from services.dungeon_expedition_service import (
    DUNGEON_POOL, get_dungeon_loot, get_group_event, join_dungeon,
    render_spawn_text, sell_all_dungeon_loot, set_event_message, spawn_group_dungeon,
)

router = Router(name="dungeon_expedition")
logger = logging.getLogger(__name__)


async def _dungeon_language(user_id: int) -> str:
    try:
        from services.language_service import get_language
        return await get_language(user_id)
    except Exception:
        return "fa"


def _dungeon_translate(text: str, language: str) -> str:
    if language == "fa":
        return text
    translations = {
        "🚪 ورود به دانجن": ("🚪 Enter Dungeon", "🚪 Войти в подземелье"),
        "📜 قوانین اکتشاف": ("📜 Expedition Rules", "📜 Правила экспедиции"),
        "🟢 اعلام آمادگی": ("🟢 Ready", "🟢 Готов"),
        "🔄 تازه‌سازی وضعیت": ("🔄 Refresh Status", "🔄 Обновить статус"),
        "🔄 وضعیت اکتشاف": ("🔄 Expedition Status", "🔄 Статус экспедиции"),
        "🔄 بررسی دانجن": ("🔄 Check Dungeon", "🔄 Проверить подземелье"),
        "⌛ مهلت باقی‌مانده برای ورود:": ("⌛ Time left to enter:", "⌛ Осталось времени на вход:"),
        "🌀 <b>پارتی در آستانهٔ ورود به ": ("🌀 <b>Party preparing to enter ", "🌀 <b>Группа готовится войти в "),
        "🧭 درجه:": ("🧭 Difficulty:", "🧭 Сложность:"),
        "🎚 سطح پیشنهادی:": ("🎚 Recommended level:", "🎚 Рекомендуемый уровень:"),
        "👥 اعضای پارتی:": ("👥 Party members:", "👥 Участники группы:"),
        "🟢 آماده:": ("🟢 Ready:", "🟢 Готовы:"),
        "⏳ زمان باقی‌مانده برای آمادگی:": ("⏳ Time left to get ready:", "⏳ Осталось времени на подготовку:"),
        "هر عضو باید خودش دکمهٔ «اعلام آمادگی» را بزند.": ("Each member must press “Ready” themselves.", "Каждый участник должен сам нажать «Готов»."),
        "🌌 <b>اکتشاف در جریان است: ": ("🌌 <b>Expedition in progress: ", "🌌 <b>Экспедиция проходит: "),
        "⏳ زمان باقی‌مانده:": ("⏳ Time remaining:", "⏳ Осталось времени:"),
        "قهرمانان در مسیرند؛ گزارش و غنیمت‌ها پس از پایان به پیام خصوصی ارسال می‌شود.": ("Heroes are on their way; the report and loot will be sent by private message when finished.", "Герои в пути; отчёт и добыча будут отправлены в личные сообщения после завершения."),
        "🌫️ <b>این دروازه بسته شده است.</b>": ("🌫️ <b>This gate is closed.</b>", "🌫️ <b>Эти врата закрыты.</b>"),
        "برای دانجن بعدی منتظر بمانید.": ("Wait for the next dungeon.", "Дождитесь следующего подземелья."),
        "🗝 <b>صندوقچهٔ غنیمت‌های دانجن</b>": ("🗝 <b>Dungeon Loot Chest</b>", "🗝 <b>Сундук добычи подземелья</b>"),
        "هنوز یادگاری‌ای از ژرفای دانجن‌ها پیدا نکرده‌ای.": ("You have not found any dungeon loot yet.", "Вы ещё не нашли добычу в подземельях."),
        "این یادگارها فقط از دانجن به دست می‌آیند و با تجهیزات یا آیتم‌های فروشگاه قاطی نمی‌شوند.": ("This loot comes only from dungeons and is kept separate from equipment and shop items.", "Эта добыча доступна только в подземельях и хранится отдельно от экипировки и товаров магазина."),
        "ارزش هر عدد:": ("Value each:", "Цена за штуку:"),
        "💰 ارزش کل صندوقچه:": ("💰 Total chest value:", "💰 Общая стоимость сундука:"),
        "💰 فروش همهٔ غنیمت‌ها": ("💰 Sell All Loot", "💰 Продать всю добычу"),
        "💰 <b>معاملهٔ غنیمت‌ها انجام شد!</b>": ("💰 <b>Loot sold successfully!</b>", "💰 <b>Добыча успешно продана!</b>"),
        "گلد دریافت‌شده:": ("Gold received:", "Получено золота:"),
        "🔄 صندوقچهٔ دانجن": ("🔄 Dungeon Chest", "🔄 Сундук подземелья"),
        "فروش انجام شد.": ("Sale completed.", "Продажа завершена."),
        "وضعیت تازه شد.": ("Status refreshed.", "Статус обновлён."),
        "هنوز دانجنی در این گپ ظاهر نشده است.": ("No dungeon has appeared in this group yet.", "В этой группе ещё не появилось подземелье."),
        "⛔ دسترسی ندارید.": ("⛔ Access denied.", "⛔ Доступ запрещён."),
        "ورود به دانجن فقط از داخل گپی انجام می‌شود که دروازه در آن ظاهر شده.": ("You can only enter from the group where the gate appeared.", "Войти можно только из группы, где появились врата."),
        "این دکمه فقط داخل گروه دانجن کار می‌کند.": ("This button only works in the dungeon group.", "Эта кнопка работает только в группе подземелья."),
        "❌ ارسال پیام به گروه ناموفق بود؛ مطمئن شو ربات هنوز عضو گروه است.": ("❌ Could not send a message to the group; make sure the bot is still a member.", "❌ Не удалось отправить сообщение в группу; убедитесь, что бот всё ещё состоит в ней."),
    }
    index = 0 if language == "en" else 1
    for source, options in translations.items():
        text = text.replace(source, options[index])
    return text



def event_keyboard(status: str = "waiting") -> InlineKeyboardMarkup:
    if status == "waiting":
        rows = [[InlineKeyboardButton(text="🚪 ورود به دانجن", callback_data="dungeon:enter")],
                [InlineKeyboardButton(text="📜 قوانین اکتشاف", callback_data="dungeon:rules")]]
    elif status == "forming":
        rows = [[InlineKeyboardButton(text="🟢 اعلام آمادگی", callback_data="dungeon:ready")],
                [InlineKeyboardButton(text="🔄 تازه‌سازی وضعیت", callback_data="dungeon:refresh")]]
    elif status == "running":
        rows = [[InlineKeyboardButton(text="🔄 وضعیت اکتشاف", callback_data="dungeon:refresh")]]
    else:
        rows = [[InlineKeyboardButton(text="🔄 بررسی دانجن", callback_data="dungeon:refresh")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def event_text(event: GroupDungeonEvent) -> str:
    names = next((d for d in DUNGEON_POOL if d["key"] == event.dungeon_key), DUNGEON_POOL[0])
    if event.status == "waiting":
        remaining = max(0, 30 - int((datetime.utcnow() - (event.spawned_at or datetime.utcnow())).total_seconds() // 60))
        return render_spawn_text({**names, "difficulty": event.difficulty, "level": event.recommended_level, "duration": event.duration_minutes}) + f"\n\n⌛ مهلت باقی‌مانده برای ورود: <b>{remaining} دقیقه</b>"
    if event.status == "forming":
        members = _ids(event.members_json); ready = _ids(event.ready_json)
        remaining = max(0, int(((event.ready_deadline or datetime.utcnow()) - datetime.utcnow()).total_seconds()))
        return (f"🌀 <b>پارتی در آستانهٔ ورود به {html.escape(event.dungeon_name)}</b>\n\n"
                f"🧭 درجه: <b>{html.escape(event.difficulty)}</b> · 🎚 سطح پیشنهادی: <b>{event.recommended_level}+</b>\n"
                f"👥 اعضای پارتی: <b>{len(members)}</b> · 🟢 آماده: <b>{len(ready)}</b>\n"
                f"⏳ زمان باقی‌مانده برای آمادگی: <b>{remaining} ثانیه</b>\n\nهر عضو باید خودش دکمهٔ «اعلام آمادگی» را بزند.")
    if event.status == "running":
        left = max(0, int(((event.finishes_at or datetime.utcnow()) - datetime.utcnow()).total_seconds()))
        return (f"🌌 <b>اکتشاف در جریان است: {html.escape(event.dungeon_name)}</b>\n\n"
                f"🧭 درجه: <b>{html.escape(event.difficulty)}</b>\n⏳ زمان باقی‌مانده: <b>{left // 60} دقیقه و {left % 60} ثانیه</b>\n\n"
                "قهرمانان در مسیرند؛ گزارش و غنیمت‌ها پس از پایان به پیام خصوصی ارسال می‌شود.")
    if event.status == "completed":
        return f"🏆 <b>اکتشاف {html.escape(event.dungeon_name)} پایان یافته است.</b>\nدروازهٔ بعدی طبق چرخهٔ گروه ظاهر خواهد شد."
    return "🌫️ <b>این دروازه بسته شده است.</b>\nبرای دانجن بعدی منتظر بمانید."


def _ids(raw: str | None) -> list[int]:
    import json
    try: return [int(x) for x in json.loads(raw or "[]")]
    except (ValueError, TypeError): return []

async def _show_event(message: Message, chat_id: int):
    event = await get_group_event(chat_id)
    if not event:
        await message.answer("🌫️ هنوز دروازه‌ای در این گپ ظاهر نشده است. هر گپ چرخهٔ مستقل خودش را دارد.")
        return
    await message.answer(event_text(event), reply_markup=event_keyboard(event.status), parse_mode="HTML")

@router.message(Command("dungeon"))
@router.message(F.text.regexp(r"^غنیمت[ \u200c]+دانجن$"))
async def dungeon_loot_phrase(message: Message):
    await _show_loot(message)

@router.message(F.text.regexp(r"^(?:دانجن|دانجن@\w+)$"))
async def dungeon_command(message: Message):
    if message.chat.type in {"group", "supergroup"}:
        await _show_event(message, message.chat.id)
    else:
        await _show_loot(message)

@router.callback_query(F.data == "menu:dungeon")
async def dungeon_menu(callback: CallbackQuery):
    if callback.message and callback.message.chat.type in {"group", "supergroup"}:
        event = await get_group_event(callback.message.chat.id)
        if event:
            try: await callback.message.edit_text(event_text(event), reply_markup=event_keyboard(event.status), parse_mode="HTML")
            except Exception: pass
            await callback.answer()
        else:
            await callback.answer("هنوز دانجنی در این گپ ظاهر نشده است.", show_alert=True)
    else:
        if callback.message:
            await _show_loot(callback.message)
        await callback.answer()

@router.callback_query(F.data == "dungeon:rules")
async def dungeon_rules(callback: CallbackQuery):
    await callback.answer("هر گپ دانجن تصادفی خودش را دارد؛ فقط یک پارتی می‌تواند وارد شود. مهلت ورود ۳۰ دقیقه و مهلت آمادگی اعضا یک دقیقه است.", show_alert=True)

@router.callback_query(F.data == "dungeon:enter")
async def dungeon_enter(callback: CallbackQuery):
    if not callback.message or callback.message.chat.type not in {"group", "supergroup"}:
        await callback.answer("ورود به دانجن فقط از داخل گپی انجام می‌شود که دروازه در آن ظاهر شده.", show_alert=True); return
    ok, message, data = await join_dungeon(callback.message.chat.id, callback.from_user.id)
    if not ok:
        await callback.answer(message, show_alert=True); return
    event = await get_group_event(callback.message.chat.id)
    if event:
        try: await callback.message.edit_text(event_text(event), reply_markup=event_keyboard(event.status), parse_mode="HTML")
        except Exception: pass
    await callback.answer(message, show_alert=True)

@router.callback_query(F.data == "dungeon:ready")
async def dungeon_ready(callback: CallbackQuery):
    if not callback.message or callback.message.chat.type not in {"group", "supergroup"}:
        await callback.answer("این دکمه فقط داخل گروه دانجن کار می‌کند.", show_alert=True); return
    ok, message, data = await join_dungeon(callback.message.chat.id, callback.from_user.id)
    if not ok:
        await callback.answer(message, show_alert=True); return
    event = await get_group_event(callback.message.chat.id)
    if event:
        try: await callback.message.edit_text(event_text(event), reply_markup=event_keyboard(event.status), parse_mode="HTML")
        except Exception: pass
    await callback.answer(message, show_alert=True)

@router.callback_query(F.data == "dungeon:refresh")
async def dungeon_refresh(callback: CallbackQuery):
    if not callback.message:
        await callback.answer(); return
    event = await get_group_event(callback.message.chat.id)
    if event:
        try: await callback.message.edit_text(event_text(event), reply_markup=event_keyboard(event.status), parse_mode="HTML")
        except Exception: pass
    await callback.answer("وضعیت تازه شد.")

async def _show_loot(message: Message):
    rows = await get_dungeon_loot(message.from_user.id if message.from_user else 0)
    if not rows:
        await message.answer("🗝 <b>صندوقچهٔ غنیمت‌های دانجن</b>\n\nهنوز یادگاری‌ای از ژرفای دانجن‌ها پیدا نکرده‌ای.", parse_mode="HTML")
        return
    total = sum(int(x.quantity) * int(x.unit_gold) for x in rows)
    lines = ["🗝 <b>صندوقچهٔ غنیمت‌های دانجن</b>", "", "این یادگارها فقط از دانجن به دست می‌آیند و با تجهیزات یا آیتم‌های فروشگاه قاطی نمی‌شوند.", ""]
    for item in rows:
        lines.append(f"✧ <b>{html.escape(item.item_name)}</b> ×{item.quantity}\n   ارزش هر عدد: 💰 {item.unit_gold:,} · جمع: <b>{item.quantity * item.unit_gold:,}</b>")
    lines.extend(["", f"💰 ارزش کل صندوقچه: <b>{total:,} گلد</b>"])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💰 فروش همهٔ غنیمت‌ها", callback_data="dungeon:loot:sell_all")]])
    await message.answer("\n".join(lines), reply_markup=protect_keyboard(keyboard, message.from_user.id), parse_mode="HTML")

@router.callback_query(F.data == "dungeon:loot:sell_all")
async def dungeon_sell_all(callback: CallbackQuery):
    ok, msg, total, sold = await sell_all_dungeon_loot(callback.from_user.id)
    if callback.message:
        text = (f"💰 <b>معاملهٔ غنیمت‌ها انجام شد!</b>\n\n{html.escape(msg)}\nگلد دریافت‌شده: <b>+{total:,}</b>" if ok else html.escape(msg))
        try: await callback.message.edit_text(text, reply_markup=protect_keyboard(InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 صندوقچهٔ دانجن", callback_data="dungeon:loot:refresh")]]), callback.from_user.id), parse_mode="HTML")
        except Exception: await callback.message.answer(text, parse_mode="HTML")
    await callback.answer("فروش انجام شد." if ok else msg, show_alert=not ok)

@router.callback_query(F.data == "dungeon:loot:refresh")
async def dungeon_loot_refresh(callback: CallbackQuery):
    if callback.message:
        rows = await get_dungeon_loot(callback.from_user.id)
        total = sum(int(x.quantity) * int(x.unit_gold) for x in rows)
        lines = ["🗝 <b>صندوقچهٔ غنیمت‌های دانجن</b>"]
        for x in rows: lines.append(f"✧ <b>{html.escape(x.item_name)}</b> ×{x.quantity} · 💰 {x.unit_gold:,} هر عدد")
        lines.append(f"\n💰 ارزش کل: <b>{total:,}</b>")
        keyboard = protect_keyboard(InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💰 فروش همهٔ غنیمت‌ها", callback_data="dungeon:loot:sell_all")]]), callback.from_user.id)
        await callback.message.answer("\n".join(lines), reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# Admin manual spawn controls; authorization is always checked against configured ADMIN_ID.
@router.callback_query(F.data == "admin:dungeon:spawn")
async def admin_dungeon_spawn_menu(callback: CallbackQuery):
    if callback.from_user.id != settings.admin_id:
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True); return
    async with AsyncSessionLocal() as session:
        groups = list((await session.scalars(select(GroupBoss).order_by(GroupBoss.chat_title))).all())
    rows = [[InlineKeyboardButton(text=f"{(g.chat_title or str(g.chat_id))[:32]} · {g.chat_id}", callback_data=f"admin:dungeon:target:{g.chat_id}")] for g in groups]
    if not rows: rows = [[InlineKeyboardButton(text="هنوز گروهی ثبت نشده است", callback_data="admin:home")]]
    rows.append([InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="admin:home")])
    if callback.message:
        await callback.message.edit_text("🌌 <b>اسپان دستی دانجن</b>\n\nگروه مقصد را انتخاب کن. سطح و نوع دانجن به‌صورت تصادفی تعیین می‌شود.", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("admin:dungeon:target:"))
async def admin_dungeon_spawn_target(callback: CallbackQuery):
    if callback.from_user.id != settings.admin_id:
        await callback.answer("⛔ دسترسی ندارید.", show_alert=True); return
    try: chat_id = int((callback.data or "").rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer("گروه نامعتبر است.", show_alert=True); return
    async with AsyncSessionLocal() as session:
        group = await session.scalar(select(GroupBoss).where(GroupBoss.chat_id == chat_id))
    if not group:
        await callback.answer("گروه پیدا نشد.", show_alert=True); return
    ok, data = await spawn_group_dungeon(chat_id, group.chat_title, force=True)
    if not ok:
        await callback.answer(data, show_alert=True); return
    try:
        sent = await bot.send_message(chat_id, render_spawn_text(data), reply_markup=event_keyboard("waiting"), parse_mode="HTML")
        await set_event_message(chat_id, sent.message_id)
        result = f"✅ دانجن {data['name']} در گروه «{html.escape(group.chat_title)}» اسپان شد."
    except Exception:
        logger.exception("Manual dungeon spawn failed for chat %s", chat_id)
        result = "❌ ارسال پیام به گروه ناموفق بود؛ مطمئن شو ربات هنوز عضو گروه است."
    if callback.message:
        await callback.message.edit_text(result, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="admin:home")]]), parse_mode="HTML")
    await callback.answer("انجام شد." if ok else "ناموفق", show_alert=not ok)
